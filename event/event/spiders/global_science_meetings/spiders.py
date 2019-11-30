from urllib import parse
import json

import scrapy
import scrapy.http

import common.util as util

from event.items import ResponseItem


class GlobalScienceMeetingsEventSpider(scrapy.Spider):

    name = 'global_science_meetings_event'
    base_url = 'http://www.globalsciencemeetings.com'
    source = 'Global Science Meetings'
    custom_settings = {
        'ITEM_PIPELINES': {
            'event.spiders.global_science_meetings.pipelines.GlobalScienceMeetingsEventPipeline': 400,
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
        yield scrapy.Request(f'{self.base_url}/Events.aspx')

    def parse(self, response: scrapy.http.Response, **kwargs):
        form_data = {
            '__VIEWSTATE': response.xpath('//input[@id="__VIEWSTATE"]/@value').get(),
            '__VIEWSTATEGENERATOR': response.xpath('//input[@id="__VIEWSTATEGENERATOR"]/@value').get(),
            '__EVENTVALIDATION': response.xpath('//input[@id="__EVENTVALIDATION"]/@value').get(),
        }

        next_page_btn = response.xpath(
            '//a[contains(@href, "Page$Next")]').get()

        if next_page_btn is not None:
            data = form_data.copy()
            data['__EVENTTARGET'] = 'grdSQL'
            data['__EVENTARGUMENT'] = 'Page$Next'

            yield scrapy.FormRequest(f'{self.base_url}/Events.aspx', formdata=data)

        entries = response.xpath(
            '//table[@id="grdSQL"]//tr[@onmouseover]').getall()

        for i, entry in enumerate(entries):
            data = form_data.copy()
            data['__EVENTTARGET'] = 'grdSQL'
            data['__EVENTARGUMENT'] = f'SysRowSelector${i}'

            yield scrapy.FormRequest(f'{self.base_url}/Events.aspx', formdata=data,
                                     callback=self.parse_entry, meta={'row_index': i})

    def parse_entry(self, response: scrapy.http.Response, **kwargs):
        yield ResponseItem({'body': response.text, 'meta': response.meta})
