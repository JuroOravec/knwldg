from collections import deque
import time

import scrapy
from selenium.common.exceptions import NoSuchElementException

from common.util import xpath_class
from common.components import SeleniumSpiderMixin

from event.items import ResponseItem


class SwissBiotechEventSpider(SeleniumSpiderMixin):

    name = 'swiss_biotech_event'
    base_url = 'https://www.swissbiotech.org'
    events_path = '/events/'
    source = 'Swiss Biotech'
    headless = False
    custom_settings = {
        'ITEM_PIPELINES': {
            'event.spiders.swiss_biotech.pipelines.SwissBiotechEventPipeline': 400,
            'event.pipelines.EventTypePipeline': 401,
            'event.pipelines.EventLocationPipeline': 402,
            'event.pipelines.EventDatePipeline': 403,
            'event.pipelines.UrlCleanerPipeline': 404,
            'event.pipelines.EventMetadataPipeline': 405,
            'event.pipelines.StripperPipeline': 406,
            'event.pipelines.WhitespaceNormalizerPipeline': 407,
            'common.pipelines.CsvWriterPipeline': 900,
        },
    }

    def start_requests(self):
        def parse_page(webdriver):
            pages = deque([])
            data = []  # list of tuples (url, organizer)
            while True:
                entry_links = webdriver.find_elements_by_xpath(
                    f'//div[@id="finderListings"]//div[{xpath_class(["grid-item"])}]//div[{xpath_class(["lf-item"])}]//a')
                entry_urls = [link.get_attribute('href')
                              for link in entry_links]
                # Sometimes, host info is missing in the entry page, so scrape it here
                organizers = [
                    o.text.split(':')[-1]
                    for o in webdriver.find_elements_by_xpath(
                        f'//ul[{xpath_class(["details-list"])}]//span')
                ]

                data.extend(zip(entry_urls, organizers))

                try:
                    next_page_el = webdriver.find_element_by_xpath(
                        f'//nav[{xpath_class(["job-manager-pagination"])}]//a[@data-page and text()="→"]')
                    next_page_num = next_page_el.get_attribute('data-page')
                    pages.append(
                        f'{self.base_url}{self.events_path}?pg={next_page_num}')
                except NoSuchElementException:
                    pass

                if len(pages) == 0:
                    break
                webdriver.get(pages.popleft())
                time.sleep(1)
            return data

        task_results = self.run_webdriver_tasks(self.webdriver, tasks=[parse_page],
                                                start_url=f'{self.base_url}{self.events_path}')
        entry_data = task_results[0]

        for url, organizer in entry_data:
            yield scrapy.Request(url, meta={'organizer': organizer})

    def parse(self, response: scrapy.http.Response, **kwargs):
        yield ResponseItem({'body': response.text, 'meta': response.meta})
