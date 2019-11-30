# -*- coding: utf-8 -*-
'''
Biotechnology Innovation Organization (BIO) pipelines

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


class BIOEventPipeline(object):
    def process_item(self, item: ResponseItem, spider):

        def parse_date(datestring):
            # parses dates in format:
            # Month DD, YYYY
            # Month DD, YYYY - Month DD, YYYY
            # Month DD - DD, YYYY
            # Month DD - Month DD, YYYY
            if datestring is None:
                return None
            ds = datestring.strip()
            if ds.count('-') == 0:
                ds = f'{ds} - {ds}'
            start, end = [s.strip() for s in ds.split('-')]
            # Add year to the start date if missing
            if ',' not in start:
                start = f'{start}{end[ end.index(",") :]}'
            # Add month to the end date if missing
            if not end[0].isalpha():
                end = f'{start[: start.index(" ") + 1]}{end}'
            return [datetime.datetime.strptime(s, '%B %d, %Y') for s in [start, end]]

        def parse_location(loc):
            # location is in form of
            # 'CityName CountryOrStateName'
            # But there is no clear distinction between state or country,
            # so we try to guess by searching for state names or abbreviations
            country = None
            state = None
            if loc.count(',') > 0:
                city, state_or_country = [s.strip() for s in loc.split(',')]
            else:
                city, state_or_country = 2 * [loc]
            for s in pycountry.subdivisions:
                for subdiv_id in [s.name, s.code.split('-')[-1]]:
                    if subdiv_id is not None and subdiv_id == state_or_country:
                        state = s.name
                        country = s.country.name
                        break
                if state is not None:
                    break
            if country is None:
                country = state_or_country
            return city, state, country

        res = scrapy.Selector(text=item['body'])

        name = res.xpath(
            f"normalize-space(string(//a[{xpath_class(['event-name'])}]))").get()
        desc = res.xpath(
            f"//td[{xpath_class(['desc-cell'])}]/text()").get()
        location = res.xpath(
            f"//td[{xpath_class(['loc-cell'])}]/text()").get()

        date = res.xpath(
            f"//td[{xpath_class(['views-field-field-date'])}]/text()").get('-')
        event_url = res.xpath(
            f"//a[{xpath_class(['event-name'])}]/@href").get()

        start, end = parse_date(date)
        city, state, country = parse_location(location)

        event = EventItem()

        event['name'] = name
        event['event_url'] = f'{spider.base_url}{event_url}'
        event['description'] = desc

        # event['focus'] = scrapy.Field()
        # event['event_type'] = scrapy.Field()

        event['start'] = start
        event['end'] = end
        # event['length_in_days'] = scrapy.Field()

        event['country'] = country
        event['state'] = state
        event['city'] = city
        # event['venue'] = scrapy.Field()

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

        # event['organizer'] = scrapy.Field()
        # event['organizer_url'] = scrapy.Field()

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
