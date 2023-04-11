from abc import ABC, abstractmethod
import time
from datetime import datetime
from urllib import parse
import re

import scrapy


'''
If there will ever be a need to scale, see http://blog.paracode.com/2017/10/29/building-market-analysis-products/
'''


class SKMoJRegistrySpider(ABC):
    """
    Scrapes entries from the Registries of Slovak Ministry of Justice
    Data taken from http://www.orsr.sk/,
    Run by the Ministry of Justice of the Slovak Republic
    """

    sources = []
    sources_delim = " "

    country = "Slovakia"
    economic_area = "EEA"
    liquidation_code = "v likvidácii"

    max_entries_per_page = 500

    custom_settings = {
        'ITEM_PIPELINES': {
            'skveda.pipelines.CsvWriterPipeline': 400
        }
    }

    @property
    @abstractmethod
    def name(self):
        ...

    @abstractmethod
    def resolve_too_many_entries(self, response):
        ...

    def __init__(self, sources=None, sources_delim=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if sources_delim is not None:
            self.sources_delim = sources_delim
            self.logger.debug(
                f'Sources delimiter set to "{self.sources_delim}"')
        if sources is not None:
            self.sources = sources.split(self.sources_delim)
            self.logger.debug('Sources: "{}"'.format(
                '", "'.join(self.sources)))

    def start_requests(self):
        if self.sources:
            for source in self.sources:
                self.logger.debug(f'Opening source "{source}"')
                with open(source, "r") as f:
                    for line in f:
                        for url in self.process_source_line(line):
                            yield url
        else:
            for url in self.custom_start_requests():
                yield url

    def parse(self, response):
        # entry url
        if self.is_entry(response.url):
            yield next(self.parse_entry(response))
        # search url
        else:
            for url_req in self.parse_search(response):
                yield url_req

    def parse_search(self, response):
        entries_num_selector = '//body/table[2]//td[2]/b[2]/text()'
        entry_selector = f'//body/table[3]//td[position()=3]//div[{self.xpath_class(["bmk"])} and position()=1]/a[1]/@href'

        def get_page_entries_info(response):
            entries_info = response.xpath(entries_num_selector).get()
            start, end, total = map(
                int,
                entries_info.replace("/", "-").split("-")
            )
            return start, end, total

        def is_last_page(displayed, total):
            return displayed >= total

        def get_next_page_url(response):
            url_obj, q_obj = self.unpack_url(response)
            q_obj["STR"] = int(q_obj.get("STR", 1)) + 1
            return self.pack_url(url_obj, q_obj)

        # follow links to entry pages
        entries = response.xpath(entry_selector).getall()
        for href in entries:
            yield response.follow(href, self.parse_entry)

        # follow pagination links
        _, displayed, total = get_page_entries_info(response)

        if total > self.max_entries_per_page:
            new_urls = self.resolve_too_many_entries(response)
        elif not is_last_page(displayed, total):
            new_urls = [get_next_page_url(response)]
        else:
            new_urls = []

        for new_url in new_urls:
            yield response.follow(new_url, self.parse_search)

        # self.logger.debug(f"entries_found = {len(entries)}")
        # self.logger.debug(f"is_last_page = {is_last_page(response)}")

    def parse_entry(self, response):

        def city_from_address(a):
            def is_postcode(s):
                try:
                    int(s.replace(" ", ""))
                    return True
                except ValueError:
                    return False

            a_parts = a.split("\r")

            if len(a_parts) == 1:
                city = a if is_postcode(a) else ""
            else:
                # Last line can be postcode or city
                city = a_parts[-2] if is_postcode(a_parts[-1]) else a_parts[-1]

            return city.split("-")[0].strip()

        meta_field_parent_selector = f'//body/table[3]//span[{self.xpath_class(["tl"])}]/parent::td'
        meta_field_title_selector = f'/descendant::span[{self.xpath_class(["tl"])}]/text()'
        meta_field_value_selector = f'/descendant::span[{self.xpath_class(["ra", "ro"])}]/text()'

        field_parent_selector = f'//body/table[position()>3]//span[{self.xpath_class(["tl"])}]/ancestor::tr'
        field_title_selector = f'/descendant::td[position()=1]/span[{self.xpath_class(["tl"])}]/text()'
        field_value_selector = f'/descendant::td[position()=2]//td[position()=1]//span[{self.xpath_class(["ra", "ro"])}]/text()'

        meta_fields, fields = map(
            self.parse_entry_fields,
            [response] * 2,
            [meta_field_parent_selector, field_parent_selector],
            [meta_field_title_selector, field_title_selector],
            [meta_field_value_selector, field_value_selector]
        )

        names = [fields[k] for k in fields if "obchodné meno" in k]
        liquidation = (
            [self.is_in_liquidation(name) for name in names] or [False]
        )[0]
        addresses = [fields[k] for k in fields if "sídlo" in k]
        city = (
            [city_from_address(a) for a in addresses] or [""]
        )[0]

        data = {
            **meta_fields,
            **fields,
            'city': city,
            'country': self.country,
            'economic_area': self.economic_area,
            'registry': response.url,
            'liquidation': liquidation,
            'timestamp': int(time.time() * 1000)
        }

        if "ičo" in data:
            data["ičo"] = "".join(data["ičo"].split())
        if "deň zápisu" in data:
            data["deň zápisu (timestamp)"] = int(datetime.strptime(
                "".join(data["deň zápisu"].split()),
                "%d.%m.%Y"
            ).timestamp() * 1000)
        if "deň výmazu" in data:
            data["deň výmazu (timestamp)"] = int(datetime.strptime(
                "".join(data["deň výmazu"].split()),
                "%d.%m.%Y"
            ).timestamp() * 1000)

        yield data

    def parse_entry_fields(self, response, parent_selector, title_selector, value_selector):

        def get_title(el, selector):
            title = el.xpath(selector).get("").replace(":", "").strip().lower()
            # self.logger.debug(f"\nselector: {selector}\ntitle: {title}\n")
            return title

        def get_value(el, selector):
            value = self.multiline(self.unquote(
                "\n".join(
                    map(str.strip, el.xpath(value_selector).getall())
                )
            ))
            # self.logger.debug(f"\nselector: {selector}\nvalue: {value}\n")
            return value

        parents = [
            scrapy.http.TextResponse("", body=el.get(), encoding="utf-8")
            for el in response.xpath(parent_selector)
        ]

        data = {
            get_title(el, title_selector): get_value(el, value_selector)
            for el in parents
        }

        return data

    def unpack_url(self, response=None, url=None):
        url = url if url is not None else response.url

        def first_dict_vals(d):
            return {
                k: v[0]
                for k, v in d.items()
            }
        url_obj = parse.urlparse(url)
        q_obj = parse.parse_qs(url_obj.query)
        q_obj = first_dict_vals(q_obj)
        return url_obj, q_obj

    def pack_url(self, url_obj, q_obj):
        url_obj = url_obj._replace(query=parse.urlencode(q_obj))
        url_string = parse.urlunparse(url_obj)
        return url_string

    def process_source_line(self, line):
        yield scrapy.Request(line.strip())

    def is_entry(self, url):
        return "orsr.sk/vypis.asp" in url

    def is_in_liquidation(self, name):
        return self.liquidation_code in name

    def unquote(self, s):
        while len(s) and s[0] == s[-1] and all(c in '\'"' for c in [s[0], s[-1]]):
            s = s[1:-1]
        return s

    def multiline(self, s):
        return s.replace('\n', '\r')

    def xpath_class(self, classes):
        return " or ".join(
            f"contains(concat(' ', normalize-space(@class),' '),' {cls} ')"
            for cls in classes
        )


class SKMoJBusinessesByIdSpider(SKMoJRegistrySpider, scrapy.Spider):
    """
    Scrapes entries from the Business Registry of Slovak Ministry of Justice
    Data taken from http://www.orsr.sk/,
    Run by the Ministry of Justice of the Slovak Republic
    """

    name = "businesses_by_id"

    id_digit_len = 8
    start = 0
    end = -1

    def custom_start_requests(self):
        count = self.start
        if end < 0:
            max = pow(10, self.id_digit_len)
        else:
            max = end

        while count < max:
            id = str(count).zfill(self.id_digit_len)
            yield scrapy.Request(f"http://www.orsr.sk/hladaj_ico.asp?ICO={id}&SID=0")
            count += 1

    def resolve_too_many_entries(self, response):
        url_obj, q_obj = self.unpack_url(response)
        # Court Codes:
        # 1 - Any
        # 2 - Bratislava I
        # 3 - Banska Bystrica
        # 4 - Kosice I
        # 5 - Zilina
        # 6 - Trencin
        # 7 - Trnava
        # 8 - Presov
        # 9 - Nitra
        for sid in range(2, 10):
            q = q_obj.copy()
            q["SID"] = sid
            yield self.pack_url(url_obj, q)


class SKMoJBusinessesByNameSpider(SKMoJRegistrySpider, scrapy.Spider):
    """
    Scrapes entries from the Business Registry of Slovak Ministry of Justice
    Data taken from http://www.orsr.sk/,
    Run by the Ministry of Justice of the Slovak Republic
    """

    name = "businesses_by_name"

    sources = ""
    sources_delim = " "
    valid_chars = "abcdefghijklmnopqrstuvwxyz0123456789"
    query_min_size = 1
    start = ""
    end = ""
    pattern = ""

    def __init__(self, sources=None, valid_chars=None, start=None, end=None, pattern=None, query_min_size=None, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if sources is not None:
            self.sources = sources.split()
        if valid_chars is not None:
            self.valid_chars = valid_chars
        if start is not None:
            self.start = start
        if end is not None:
            self.end = end
        if pattern is not None:
            self.pattern = pattern
        if query_min_size is not None:
            self.query_min_size = int(query_min_size)

        self._pattern = re.compile(self.pattern)

    def process_source_line(self, line):
        if self.is_entry(line):
            return scrapy.Request(line.strip())

        url_obj, q_obj = self.unpack_url(url=line.strip())
        name = q_obj.get('OBMENO', "")
        page = int(q_obj.get("STR", 1))
        i = len(name) - 1
        for url in self.search(name=name, page=page, index=i):
            yield url

    def custom_start_requests(self):
        for url in self.search():
            yield url

    def search(self, name="", page=1, index=-1):
        if len(name) >= self.query_min_size:
            # OBMENO = Business Name (Obchodne meno)
            # PF = Legal form ID (Pravna forma)
            # SID = Court ID (Sud)
            # R = "on" == active entries only
            # S = "on"== search anywhere in name; "off" == entry starts with query
            p = f"&STR={page}" if page > 1 else ""
            yield scrapy.Request(f"http://www.orsr.sk/hladaj_subjekt.asp?OBMENO={name}&PF=0&SID=0&S=off&R=on{p}")
            return

        name = bytearray(name, "ascii")
        start_reached = False
        end_reached = False
        index = index + 1

        for s in self.valid_chars:
            # Skip if start is given and has not been reached yet
            # or if end is given and has been already reached
            if (
                    self.start
                    and not start_reached
                    and len(self.start) >= index + 1
                    and s != self.start[index]
                ) \
                or \
                (
                    self.end
                    and end_reached
            ):
                continue
            if not start_reached:
                start_reached = True

            temp_name = name.copy()
            # old_name = temp_name.decode()

            # workaround for "ch" being considered a separate char.
            # uses (temp_name + variant) as a final name for all variants
            variants = [""]
            if s == "c":
                variants.append("h")
            for v in variants:
                if end_reached:
                    continue

                seq = f"{s}{v}"

                for i, c in enumerate(seq):
                    if len(temp_name) < index + 1 + i:
                        temp_name.append(ord(c))
                    else:
                        temp_name[index] = ord(c)

                if self.end and temp_name.decode() == self.end:
                    end_reached = True

                # Skip query name if it does not match the pattern
                if self.pattern and not self._pattern.search(temp_name.decode()):
                    continue

                # self.logger.debug(
                #     f"name change: {old_name} -> {temp_name.decode()}")

                urls = self.search(
                    name=temp_name.decode(),
                    index=index
                )
                for url in urls:
                    yield url

    def resolve_too_many_entries(self, response):
        url_obj, q_obj = self.unpack_url(response)
        for s in self.valid_chars:
            q = q_obj.copy()
            q["OBMENO"] = f"{q['OBMENO']}{s}"
            yield self.pack_url(url_obj, q)
