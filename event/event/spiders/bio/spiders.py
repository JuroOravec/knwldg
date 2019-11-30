import scrapy

from common.util import xpath_class

from event.items import ResponseItem


class BIOEventSpider(scrapy.Spider):

    name = 'bio_event'
    base_url = 'https://www.bio.org'
    events_path = '/events'
    source = 'BIO'
    custom_settings = {
        'ITEM_PIPELINES': {
            'event.spiders.bio.pipelines.BIOEventPipeline': 400,
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
        entries = response.xpath(
            f'//div[{xpath_class(["event-search"])}]//table/tbody/tr').getall()

        for entry in entries:
            yield ResponseItem({'body': entry, 'meta': response.meta})
