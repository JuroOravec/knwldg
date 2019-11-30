'''
Spider for WP sites that use The Events Calendar by Modern Tribe (https://theeventscalendar.com/)
'''

import scrapy
import scrapy.http

import common.util as util

from event.items import ResponseItem


class EventsCalendarSpider(scrapy.Spider):
    '''
    Spider that scrapes event entries from WP sites that use 
    The Events Calendar by Modern Tribe (https://theeventscalendar.com/)

    Spider expects two properties:
    - base_url: `str` Base url of the website
    - events_path: `str` Relative path to the events page 
    '''

    def start_requests(self):
        yield scrapy.Request(f'{self.base_url}{self.events_path}')

    def parse(self, response: scrapy.http.Response, **kwargs):
        next_page_url = response.xpath('//a[@rel="next"]/@href').get()
        if next_page_url is not None:
            yield scrapy.Request(next_page_url)

        entry_urls = response.xpath(
            f'//div[{util.xpath_class(["type-tribe_events"])}]//*[{util.xpath_class(["tribe-events-list-event-title"])}]/a/@href').getall()

        for url in entry_urls:
            yield scrapy.Request(url, callback=self.parse_entry)

    def parse_entry(self, response: scrapy.http.Response, **kwargs):
        yield ResponseItem({'body': response.text, 'meta': response.meta})
