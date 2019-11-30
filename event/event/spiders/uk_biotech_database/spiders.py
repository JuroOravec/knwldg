import scrapy

from common.util import xpath_class

from event.items import ResponseItem


class UKBiotechDatabaseEventSpider(scrapy.Spider):

    name = 'uk_biotech_database_event'
    base_url = 'http://www.ukbiotech.com'
    events_path = '/uk/portal/events.php'
    source = 'UK Biotech Database'
    custom_settings = {
        'ITEM_PIPELINES': {
            'event.spiders.uk_biotech_database.pipelines.UKBiotechDatabaseEventPipeline': 400,
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
            f'//div[{xpath_class(["event"])}]').getall()

        for entry in entries:
            yield ResponseItem({'body': entry, 'meta': response.meta})
