import json

import scrapy

from event.items import ResponseItem


class BioPartnerEventSpider(scrapy.Spider):

    name = 'bio_partner_event'
    base_url = 'http://www.biopartner.co.uk'
    events_path = '/events.php'
    source = 'Bio Partner'
    custom_settings = {
        'ITEM_PIPELINES': {
            'event.spiders.bio_partner.pipelines.BioPartnerEventPipeline': 400,
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
        yield scrapy.Request(
            url='https://biopartneruk.network-of-communities.com/events/api-v1.0.php',
            headers={
                'Referer': 'http://www.biopartner.co.uk/events.php'
            })

    def parse(self, response: scrapy.http.Response, **kwargs):
        data = json.loads(response.text)
        if data['message']:
            for msg in data['message']:
                self.logger.warning(msg)

        for entry in data['list']:
            yield ResponseItem({'body': entry, 'meta': response.meta})
