import scrapy

from common.util import xpath_class

from event.items import ResponseItem


class BIAEventSpider(scrapy.Spider):

    name = 'bia_event'
    base_url = 'https://www.bioindustry.org'
    events_path = '/events-listing.html'
    source = 'BIA'
    custom_settings = {
        'ITEM_PIPELINES': {
            'event.spiders.bia.pipelines.BIAEventPipeline': 400,
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
        entry_urls = response.xpath(
            f'//div[{xpath_class(["widget-events-item"])}]/div[{xpath_class(["widget-events-item-img"])}]/a/@href').getall()
        for url in entry_urls:
            yield scrapy.Request(url, callback=self.parse_entry)

    def parse_entry(self, response: scrapy.http.Response, **kwargs):
        yield ResponseItem({'body': response.body, 'meta': response.meta, 'url': response.url})
