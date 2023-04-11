from abc import ABC, abstractmethod
import time

import scrapy

'''
If there will ever be a need to scale, see http://blog.paracode.com/2017/10/29/building-market-analysis-products/
'''


class SKMoIRegistrySpider(ABC):
    """
    Scrapes entries from the Registries of Slovak Ministry of Interior
    Data taken from http://ives.minv.sk,
    Run by the Ministry of Interior of the Slovak Republic, Public Administration Section
    """

    country = "Slovakia"
    economic_area = "EEA"
    liquidation_code = "v likvidácii"

    @property
    @abstractmethod
    def custom_form_field_text(self):
        ...

    @property
    @abstractmethod
    def name(self):
        ...

    @property
    @abstractmethod
    def registry_code(self):
        ...

    @abstractmethod
    def parse_entry(self, response):
        ...

    @property
    def form_field_text(self):
        return {
            "legal_form": ["Legal form", "Právna forma"],
            "id": ["Identification number (IČO)", "IČO"],
            "address": ["Seat", "Sídlo"],
            "website": ["Website", "Webové sídlo"],
            "reg_id": ["Registration number", "Registračné číslo"],
            "reg_office": ["Registration Office", "Registrový úrad"],
            "reg_date": ["Date of registration", "Dátum vzniku"],
            "cancel_date": ["Date of cancellation", "Dátum zrušenia"],
            "cancel_reason": ["Legal title of Cancellation", "Právny dôvod zrušenia"],
            "liq_start_date": ["Date of liquidation start", "Dátum vstupu do likvidácie"],
            "liq_end_date": ["Date of liquidation end", "Dátum ukončenia likvidácie"],
            **self.custom_form_field_text
        }

    @property
    def start_urls(self):
        return [
            f"http://ives.minv.sk/rez/registre/pages/list.aspx?type={self.registry_code}"
        ]

    def parse(self, response):
        next_page_selector = '//a[@id="contentBody_linkNext"]'

        def is_last_page(response):
            return response.url == response.xpath(next_page_selector)

        # follow links to entry pages
        for href in response.xpath('//div[@id="contentBody_divZoznam"]//tr[@class="rr"]//td[child::a[@href]][1]/a'):
            yield response.follow(href, self.parse_entry)

        # follow pagination links
        self.logger.debug(f"IS LAST PAGE = {is_last_page(response)}")
        if not is_last_page(response):
            for href in response.xpath(next_page_selector):
                yield response.follow(href, self.parse)

    def parse_entry(self, response):
        # fields are looked up by labels, which can be in SK or EN
        address = self.extract_entry_form(response, "address")
        name = self.unquote(self.extract_entry_form(response, "name"))
        yield {
            'name': name,
            'address': address,
            'city': self.city_from_address(address),
            'country': self.country,
            'economic_area': self.economic_area,
            'website': "-" if self.is_in_liquidation(name) else self.extract_entry_form(response, "website"),
            'registry': response.url,
            'liquidation': True if self.is_in_liquidation(name) else False,
            'timestamp': int(time.time() * 1000)
        }

    def extract_entry_form(self, response, field):

        def xpath_class_selector(classes):
            return " or ".join(
                f"contains(concat(' ', normalize-space(@class),' '),' {cls} ')"
                for cls in classes
            )

        def xpath_text_selector(texts):
            return " or ".join(
                f'text()="{txt}"'
                for txt in texts
            )

        query_text = xpath_text_selector(
            self.form_field_text.get(field, [""])
        )

        form = f"div[{xpath_class_selector(['divForm'])}]"
        field_value = f"div[@class=\"label\" and {query_text}]/following-sibling::div[1]"
        # Get text of first child of .nw (e.g. for international orgs),
        # or of .text (e.g. foundations),
        # or of .cell (e.g. civil societies),
        # or of li's that contain text (e.g. municipality associations)
        text_content = f'descendant-or-self::*[\
            (parent::*[{xpath_class_selector(["nw"])}] and not({xpath_class_selector(["dat", "dtx"])}))\
            or (parent::ul and self::li and not(text()=""))\
            or ({xpath_class_selector(["text", "cell"])})\
            ]/text()'
        xpath = f"//{form}//{field_value}//{text_content}"
        res = "\n".join(s.strip() for s in response.xpath(xpath).getall())

        self.logger.debug(
            f'field="{field}", xpath="{xpath}", res="{res}"'
        )
        return res

    def city_from_address(self, a):
        return " ".join(a.split(',')[-2].split('-')[0].strip().split()[1:])

    def is_in_liquidation(self, name):
        return self.liquidation_code in name

    def unquote(self, s):
        while s[0] == s[-1] and all(c in '\'"' for c in [s[0], s[-1]]):
            s = s[1:-1]
        return s

    def multiline(self, s):
        return s.replace('\n', '\r')


class SKMoINonInvestmentFundsSpider(SKMoIRegistrySpider, scrapy.Spider):
    """
    Scrapes entries from the Registry of Non-investment Funds of Slovak Ministry of Interior
    Data taken from http://ives.minv.sk,
    Run by the Ministry of Interior of the Slovak Republic, Public Administration Section
    """

    name = "noninvestment_funds"
    registry_code = "rnf"
    custom_form_field_text = {
        "name": ["Name of fund", "Názov fondu"],
        "asset_value": ["Actual value of the foundation assets", "Aktuálna hodnota nadačného imania"],
        "founders": ["Founders (Legal persons)", "Founders (Natural persons)", "Zriaďovatelia (Právnické osoby)", "Zriaďovatelia (Fyzické osoby)"],
        "trustees": ["Statutory body: Trustee", "Štatutárny orgán: Správca"],
        "objective": ["Supported purpose", "Podporovaný účel"],
        "description": ["Description of the supported purpose", "Popis podporovaného účelu"]
    }

    def parse_entry(self, response):
        data = next(super().parse_entry(response))
        yield {
            **data,
            'asset_value': self.extract_entry_form(response, "asset_value"),
            'objective': self.multiline(self.extract_entry_form(response, "objective")),
            'description': self.multiline(self.extract_entry_form(response, "description")),
        }


class SKMoIFoundationsSpider(SKMoIRegistrySpider, scrapy.Spider):
    """
    Scrapes entries from the Registry of Foundations of Slovak Ministry of Interior
    Data taken from http://ives.minv.sk,
    Run by the Ministry of Interior of the Slovak Republic, Public Administration Section
    """

    name = "foundations"
    registry_code = "rnd"
    custom_form_field_text = {
        "name": ["Name of foundation", "Názov nadácie"],
        "asset_value": ["Actual value of the foundation assets", "Aktuálna hodnota nadačného imania"],
        "founders": ["Founders", "Zakladatelia"],
        "description": ["Welfare purpose supported by the Foundation", "Verejnoprospešný účel, ktorý nadácia podporuje"]
    }

    def parse_entry(self, response):
        data = next(super().parse_entry(response))
        yield {
            **data,
            'asset_value': self.extract_entry_form(response, "asset_value"),
            'description': self.multiline(self.extract_entry_form(response, "description")),
        }


class SKMoIIntOrganisationsSpider(SKMoIRegistrySpider, scrapy.Spider):
    """
    Scrapes entries from the Registry of Organisations with International Element of Slovak Ministry of Interior
    Data taken from http://ives.minv.sk,
    Run by the Ministry of Interior of the Slovak Republic, Public Administration Section
    """

    name = "int_organisations"
    registry_code = "omp"
    custom_form_field_text = {
        "name": ["Name of organisation", "Názov organizácie"],
        "founders": ["Persons entitled to act on behalf of the association (Natural persons)", "Osoby oprávnené konať v mene organizácie (Fyzické osoby)"],
        "description": ["Content of Activity", "Obsah činnosti"]
    }

    def parse_entry(self, response):
        data = next(super().parse_entry(response))
        yield {
            **data,
            'description': self.multiline(self.extract_entry_form(response, "description")),
        }


class SKMoINPOsSpider(SKMoIRegistrySpider, scrapy.Spider):
    """
    Scrapes entries from the Registry of Non-Profit Organisations of Slovak Ministry of Interior
    Data taken from http://ives.minv.sk,
    Run by the Ministry of Interior of the Slovak Republic, Public Administration Section
    """

    name = "npos"
    registry_code = "rno"
    custom_form_field_text = {
        "name": ["Name of organisation", "Názov organizácie"],
        "founders": ["Founders (Legal persons)", "Founders (Natural persons)", "Zakladatelia (Právnické osoby)", "Zakladatelia (Fyzické osoby)"],
        "director": ["Statutory body: Director", "Štatutárny orgán: Riaditeľ"],
        "description": ["Type of the generally beneficial services", "Druh všeobecne prospešných služieb"]
    }

    def parse_entry(self, response):
        data = next(super().parse_entry(response))
        yield {
            **data,
            'description': self.multiline(self.extract_entry_form(response, "description")),
        }


class SKMoICivilSocietiesSpider(SKMoIRegistrySpider, scrapy.Spider):
    """
    Scrapes entries from the Registry of Civil Associations of Slovak Ministry of Interior
    Data taken from http://ives.minv.sk,
    Run by the Ministry of Interior of the Slovak Republic, Public Administration Section
    """

    name = "civil_societies"
    registry_code = "oz"
    custom_form_field_text = {
        "name": ["Name of association", "Názov združenia"],
        "description": ["Objective of the Activity", "Cieľ činnosti"],
    }

    def parse_entry(self, response):
        data = next(super().parse_entry(response))
        yield {
            **data,
            'description': self.multiline(self.extract_entry_form(response, "description")),
        }


class SKMoIInterestAssociationsSpider(SKMoIRegistrySpider, scrapy.Spider):
    """
    Scrapes entries from the Registry of Interest Associations of Slovak Ministry of Interior
    Data taken from http://ives.minv.sk,
    Run by the Ministry of Interior of the Slovak Republic, Public Administration Section
    """

    name = "interest_associations"
    registry_code = "zzpo"
    custom_form_field_text = {
        "name": ["Name of association", "Názov združenia"],
        "founders": ["Founders (Legal persons)", "Zakladatelia (Právnické osoby)"],
        "director": ["Persons entitled to act on behalf of the association", "Osoby oprávnené konať v mene združenia"],
        "description": ["Fields of activities", "Oblasti činnosti"],
        "bodies": ["Bodies of association", "Orgány združenia"]
    }

    def parse_entry(self, response):

        def is_null_description(s):
            return s in ["Oblasti činnosti pre dané združenie nie sú uvedené", "Field of activities for association are not listed"]

        data = next(super().parse_entry(response))
        description = self.multiline(
            self.extract_entry_form(response, "description"))
        yield {
            **data,
            'description': "" if is_null_description(description) else description,
        }


class SKMoIProfessionalAssociationsSpider(SKMoIRegistrySpider, scrapy.Spider):
    """
    Scrapes entries from the Registry of Tradesman Associations of Slovak Ministry of Interior
    Data taken from http://ives.minv.sk,
    Run by the Ministry of Interior of the Slovak Republic, Public Administration Section
    """

    name = "professional_associations"
    registry_code = "zs"
    custom_form_field_text = {
        "name": ["Name of association", "Názov spoločenstva"],
        "description": ["Objective of the Activity", "Cieľ činnosti"],
    }

    def parse_entry(self, response):

        def is_null_description(s):
            return s in ["Oblasti činnosti pre dané združenie nie sú uvedené", "Field of activities for association are not listed"]

        data = next(super().parse_entry(response))
        description = self.multiline(
            self.extract_entry_form(response, "description"))
        yield {
            **data,
            'description': "" if is_null_description(description) else description,
        }


class SKMoIUnionsSpider(SKMoIRegistrySpider, scrapy.Spider):
    """
    Scrapes entries from the Registry of Trade Union Organisations and Employers Associations of Slovak Ministry of Interior
    Data taken from http://ives.minv.sk,
    Run by the Ministry of Interior of the Slovak Republic, Public Administration Section
    """

    name = "unions"
    registry_code = "odz"
    custom_form_field_text = {
        "name": ["Name of organisation", "Názov organizácie"],
        "description": ["Objective of the Activity", "Cieľ činnosti"],
    }

    def parse_entry(self, response):
        data = next(super().parse_entry(response))
        yield {
            **data,
            'description': self.multiline(self.extract_entry_form(response, "description")),
        }


class SKMoIOtherAssociationsSpider(SKMoIRegistrySpider, scrapy.Spider):
    """
    Scrapes entries from the Registry of Associations with Confirmed Registration of Slovak Ministry of Interior
    Data taken from http://ives.minv.sk,
    Run by the Ministry of Interior of the Slovak Republic, Public Administration Section
    """

    name = "other_associations"
    registry_code = "zpc"
    custom_form_field_text = {
        "name": ["Name of association", "Názov združenia"],
        "description": ["Objective of the Activity", "Cieľ činnosti"],
    }

    def parse_entry(self, response):
        data = next(super().parse_entry(response))
        yield {
            **data,
            'description': self.multiline(self.extract_entry_form(response, "description")),
        }


class SKMoIPoliticalPartiesSpider(SKMoIRegistrySpider, scrapy.Spider):
    """
    Scrapes entries from the Registry of Political Parties of Slovak Ministry of Interior
    Data taken from http://ives.minv.sk,
    Run by the Ministry of Interior of the Slovak Republic, Public Administration Section
    """

    name = "political_parties"
    registry_code = "ps"
    custom_form_field_text = {
        "name": ["Name of political party / movement:", "Názov politickej strany / hnutia:"],
        "abbr": ["Abbreviation of name of party / movement:", "Skratka názvu politickej strany / hnutia:"],
        "legal_form": ["Type:", "Typ:"],
        "id": ["Identification number (IČO):", "IČO:"],
        "address": ["Seat:", "Sídlo:"],
        "website": ["Website:", "Webové sídlo:"],
        "reg_id": ["Registration number:", "Registračné číslo:"],
        "reg_office": ["Registration Office:", "Registrový úrad:"],
        "reg_date": ["Date of registration:", "Dátum vzniku:"],
        "cancel_date": ["Date of cancellation:", "Dátum zrušenia:"],
        "cancel_reason": ["Legal title of Cancellation:", "Právny dôvod zrušenia:"],
        "liq_start_date": ["Date of liquidation start:", "Dátum vstupu do likvidácie:"],
        "liq_end_date": ["Date of liquidation end:", "Dátum ukončenia likvidácie:"],
    }

    def parse_entry(self, response):
        def is_null_abbr(s):
            return s in ["strana nemá zaregistrovanú skratku názvu", "strana nemá zaregistrovanú skratku"]

        data = next(super().parse_entry(response))
        abbr = self.extract_entry_form(response, "abbr")
        yield {
            **data,
            'description': self.multiline(self.extract_entry_form(response, "description")),
            'abbr': "" if is_null_abbr(abbr) else abbr,
        }


class SKMoIMunicipalityAssociationsSpider(SKMoIRegistrySpider, scrapy.Spider):
    """
    Scrapes entries from the Registry of Associations of Municipalities of Slovak Ministry of Interior
    Data taken from http://ives.minv.sk,
    Run by the Ministry of Interior of the Slovak Republic, Public Administration Section
    """

    name = "municipality_associations"
    registry_code = "zzob"
    custom_form_field_text = {
        "name": ["Name of association", "Názov združenia"],
        "municipalities": ["Founders (Municipalities)", "Zakladatelia (Obce)"],
        "director": ["Persons entitled to act on behalf of the association", "Osoby oprávnené konať v mene združenia"],
        "description": ["Fields of activities", "Oblasti činnosti"],
        "bodies": ["Bodies of association", "Orgány združenia"],
    }

    def parse_entry(self, response):
        data = next(super().parse_entry(response))
        yield {
            **data,
            'description': self.multiline(self.extract_entry_form(response, "description")),
            'municipalities': self.multiline(self.extract_entry_form(response, "municipalities"))
        }


class SKMoIPremiseOwnersSpider(SKMoIRegistrySpider, scrapy.Spider):
    """
    Scrapes entries from the Registry of Associations of the Owners of Residential and Non-residential Premises of Slovak Ministry of Interior
    Data taken from http://ives.minv.sk,
    Run by the Ministry of Interior of the Slovak Republic, Public Administration Section
    """

    name = "premise_owners"
    registry_code = "svb"
    custom_form_field_text = {
        "name": ["Name of association", "Názov spoločenstva"],
        "director": ["Persons entitled to act on behalf of the association (Natural persons)", "Osoby oprávnené konať v mene spoločenstva (Fyzické osoby)"],
        "bodies": ["Bodies of association", "Orgány spoločenstva"],
    }
