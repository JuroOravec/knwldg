from datetime import datetime

import scrapy

from common.util import xpath_class

from event.items import ResponseItem


class IBioICEventSpider(scrapy.Spider):

    name = 'ibioic_event'
    base_url = 'http://www.ibioic.com'
    events_path = '/news_and_events/events/d8/'
    source = 'IBioIC'
    custom_settings = {
        'ITEM_PIPELINES': {
            'event.spiders.ibioic.pipelines.IBioICEventPipeline': 400,
            'event.pipelines.EventTypePipeline': 401,
            'event.pipelines.EventLocationPipeline': 402,
            'event.pipelines.EventDatePipeline': 403,
            'event.pipelines.UrlCleanerPipeline': 404,
            'event.pipelines.EventMetadataPipeline': 405,
            'event.pipelines.StripperPipeline': 406,
            'event.pipelines.WhitespaceNormalizerPipeline': 407,
            'common.pipelines.CsvWriterPipeline': 900,
        }
    }

    def start_requests(self):
        yield scrapy.Request(f'{self.base_url}{self.events_path}')

    def parse(self, response: scrapy.http.Response, **kwargs):
        entries_sel = response.xpath(
            f'//div[{xpath_class(["item-feature-text", "item-list"])}]')
        entries = entries_sel.getall()
        entry_paths = entries_sel.xpath('.//span/a/@href').getall()
        urls = [f'{self.base_url}{path}' for path in entry_paths]
        for url, entry in zip(urls, entries):
            yield scrapy.Request(url, callback=self.parse_entry, meta={'list_entry': entry})

    def parse_entry(self, response: scrapy.http.Response, **kwargs):
        yield ResponseItem({'body': response.body, 'meta': response.meta, 'url': response.url})
