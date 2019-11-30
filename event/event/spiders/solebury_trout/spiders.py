# -*- coding: utf-8 -*-
'''
Solebury Trout spiders

Scrapy spiders docs: https://docs.scrapy.org/en/latest/topics/spiders.html
'''


import scrapy
import scrapy.http

import common.util as util

from event.items import ResponseItem


class SoleburyTroutEventSpider(scrapy.Spider):

    name = 'solebury_trout_event'
    base_url = 'https://www.soleburytrout.com'
    source = 'Solebury Trout'
    custom_settings = {
        'URLLENGTH_LIMIT': 5000,  # needed to accept all the event IDs in query params
        'SPIDER_MIDDLEWARES': {
            'event.spider_middleware.OutputCSVParserMiddleware': 900,
        },
        'ITEM_PIPELINES': {
            'event.spiders.solebury_trout.pipelines.SoleburyTroutEventPipeline': 400,
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
        yield scrapy.Request(f'{self.base_url}/lifesciences/calendar?qs_industry[]=life_sciences&keyword=&qs_time=4')

    def parse(self, response: scrapy.http.Response, **kwargs):
        csv_path = response.xpath(
            f'//a[{util.xpath_startswith("href", "/events/csv")}]/@href'
        ).getall()[0]
        csv_url = f'{self.base_url}{csv_path}'
        yield scrapy.Request(csv_url, callback=self.parse_csv)

    def parse_csv(self, response: scrapy.http.Response, **kwargs):
        yield ResponseItem({'body': response.text, 'meta': response.meta})
