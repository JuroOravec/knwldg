import scrapy

from common.util import xpath_class

from event.items import ResponseItem


class EuropeanBiotechnologyEventSpider(scrapy.Spider):

    name = 'european_biotechnology_event'
    base_url = 'https://european-biotechnology.com'
    events_path = '/events/'
    source = 'European Biotechnology'
    custom_settings = {
        'ITEM_PIPELINES': {
            'event.spiders.european_biotechnology.pipelines.EuropeanBiotechnologyEventPipeline': 400,
            'event.pipelines.EventTypePipeline': 401,
            'event.pipelines.EventLocationPipeline': 402,
            'event.pipelines.EventDatePipeline': 403,
            'event.pipelines.UrlCleanerPipeline': 404,
            'event.pipelines.EventMetadataPipeline': 405,
            'event.pipelines.StripperPipeline': 406,
            'common.pipelines.CsvWriterPipeline': 900,
        }
    }

    def start_requests(self):
        yield scrapy.Request(f'{self.base_url}{self.events_path}')

    def parse(self, response: scrapy.http.Response, **kwargs):
        next_page_url = response.xpath(
            f'//li[{xpath_class(["next"])}]/a/@href').get()
        if next_page_url is not None:
            yield scrapy.Request(f'{self.base_url}{next_page_url}')

        entries = response.xpath(
            f'//article[{xpath_class(["event"])}]').getall()

        for entry in entries:
            yield ResponseItem({'body': entry, 'meta': response.meta})
