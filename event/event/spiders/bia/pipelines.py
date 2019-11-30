# -*- coding: utf-8 -*-
'''
UK Bioindustry Association (BIA) pipelines

Scrapy pipelines docs: https://docs.scrapy.org/en/latest/topics/item-pipeline.html
'''

import datetime
import html
import re
from urllib import parse

import pycountry
import scrapy

from event.items import EventItem, ResponseItem
from common.util import xpath_class, lmap


class BIAEventPipeline(object):
    def process_item(self, item: ResponseItem, spider):

        def parse_date(datestring):
            # parses dates in format:
            # HH:HH, DD MMM YYYY
            # HH:HH-HH:HH, DD MMM YYYY
            # DD MMM YYYY
            # DD MMM YYYY - DD MMM YYYY
            if datestring is None:
                return None
            ds = datestring.strip()
            # Strip hour details if it's 1-day event
            if ds.count(',') > 0:
                ds = ds.split(',')[-1]
            # Normalize date range if it's 1-day event
            if ds.count('-') == 0:
                ds = f'{ds} - {ds}'
            start, end = [
                datetime.datetime.strptime(s.strip(), '%d %b %y')
                for s in ds.split('-')]
            return start, end

        def parse_location(loc):
            # location is in form of
            # 'Venue, City'
            # 'Venue'
            venue = ''
            city = ''
            if loc.count(',') > 0:
                venue, city = [s.strip() for s in loc.split(',')]
            else:
                venue = loc
            return venue, city

        res = scrapy.Selector(text=item['body'])

        name = res.xpath(f"//h1/text()").get()
        desc = res.xpath(
            f"normalize-space(string(//div[{xpath_class(['content-wrapper'])}]))").get()
        location = res.xpath(
            f"//div[{xpath_class(['after-heading-meta'])}]/ul[position()=1]/li[position()=2]/text()").get('')
        date = res.xpath(
            f"//div[{xpath_class(['after-heading-meta'])}]/ul[position()=1]/li[position()=1]/text()").get('-')
        event_type = res.xpath(
            f"//div[{xpath_class(['after-heading-meta'])}]/ul[position()=2]/li[position()=1]/text()").get()

        start, end = parse_date(date)
        venue, city = parse_location(location)

        event = EventItem()

        event['name'] = name
        event['event_url'] = item['url']
        event['description'] = desc

        # event['focus'] = scrapy.Field()
        event['event_type'] = event_type

        event['start'] = start
        event['end'] = end
        # event['length_in_days'] = scrapy.Field()

        event['country'] = 'United Kingdom'
        # event['state'] = scrapy.Field()
        event['city'] = city
        event['venue'] = venue

        # event['price'] = scrapy.Field()
        # event['currency'] = scrapy.Field()

        # event['stand'] = scrapy.Field()
        # event['abstract'] = scrapy.Field()
        # event['talk'] = scrapy.Field()

        # event['ticket_deadline'] = scrapy.Field()
        # event['stand_deadline'] = scrapy.Field()
        # event['talk_deadline'] = scrapy.Field()

        # event['contact_name'] = scrapy.Field()
        # event['contact_email'] = scrapy.Field()
        # event['contact_phone'] = scrapy.Field()

        event['organizer'] = 'BIA'
        event['organizer_url'] = spider.base_url

        # event['newsletter'] = scrapy.Field()
        # event['twitter'] = scrapy.Field()
        # event['facebook'] = scrapy.Field()
        # event['linkedin'] = scrapy.Field()
        # event['instagram'] = scrapy.Field()

        # event['hashtags'] = scrapy.Field()

        # event['relevant_to_bio'] = scrapy.Field()
        # event['relevant_to_ind_bio'] = scrapy.Field()

        # event['ignore'] = scrapy.Field()
        # event['notes'] = scrapy.Field()

        # event['source'] = scrapy.Field()
        # event['id'] = scrapy.Field()

        return event
