from datetime import datetime

import scrapy

from common.util import xpath_class

from event.items import ResponseItem


class AusbiotechEventSpider(scrapy.Spider):

    name = 'ausbiotech_event'
    base_url = 'https://www.ausbiotech.org'
    events_path = '/events/calendar_month'
    source = 'Ausbiotech'
    custom_settings = {
        'ITEM_PIPELINES': {
            'event.spiders.ausbiotech.pipelines.AusbiotechEventPipeline': 400,
            'event.pipelines.EventTypePipeline': 401,
            'event.pipelines.EventLocationPipeline': 402,
            'event.pipelines.EventDatePipeline': 403,
            'event.pipelines.UrlCleanerPipeline': 404,
            'event.pipelines.EventMetadataPipeline': 405,
            'event.pipelines.StripperPipeline': 406,
            'event.pipelines.WhitespaceNormalizerPipeline': 407,
            'common.pipelines.CsvWriterPipeline': 900,
        },
        'ROBOTSTXT_OBEY': False
    }

    def start_requests(self):
        now = datetime.now()
        curr_mo = now.month
        curr_yr = now.year
        # Get calendar for next 24 months
        for i in range(24):
            mo_total = curr_mo + i
            mo = ((mo_total - 1) % 12) + 1
            yr = curr_yr + ((mo_total - 1) // 12)
            yield scrapy.Request(f'{self.base_url}{self.events_path}?month={mo}&year={yr}')

    def parse(self, response: scrapy.http.Response, **kwargs):
        entry_paths = response.xpath(
            f'//td[{xpath_class(["eventsCalenderDayHasEvents"])}]/a/@href').getall()
        urls = [f'{self.base_url}{path}' for path in entry_paths]
        for url in urls:
            yield scrapy.Request(url, callback=self.parse_entry)

    def parse_entry(self, response: scrapy.http.Response, **kwargs):
        yield ResponseItem({'body': response.body, 'meta': response.meta, 'url': response.url})
