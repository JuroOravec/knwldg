# -*- coding: utf-8 -*-
'''
UK Biotech Database pipelines

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


class UKBiotechDatabaseEventPipeline(object):
    def process_item(self, item: ResponseItem, spider):

        def parse_date(datestring):
            if datestring is None:
                return None
            ds = datestring.strip()
            return datetime.datetime.strptime(ds, '%d %b %y')

        def parse_location(loc):
            # location is in form of
            # 'City Name Country Name'
            # But there is no clear distinction between which words belong to city
            # and which to country, so we try to guess by searching for country names
            # or abbreviations
            country = None
            for c in pycountry.countries:
                for country_id in c._fields.values():
                    if country_id in loc:
                        country = c.name
            if country is not None:
                city = loc.split(country)[0]
            else:
                city = loc
            return city, country

        res = scrapy.Selector(text=item['body'])

        name = res.xpath(
            f"//div[{xpath_class(['event_title'])}]/h3/text()").get()
        venue, location, _, desc, *__ = res.xpath(
            f"//div[{xpath_class(['event_desc'])}]").get('<br><br><br>').split('<br>')
        start, end = res.xpath(
            f"//div[{xpath_class(['event_date'])}]/b/text()").get('').split('-')
        contact_name = res.xpath(
            f"//div[{xpath_class(['event_desc', 'event_contact'], operator='and')}]").get('<br>')
        contact_email = res.xpath(
            f"//div[{xpath_class(['event_desc', 'event_contact'], operator='and')}]/a/@href").get('')
        event_url = res.xpath(
            f"//div[{xpath_class(['event_web'])}]/a/@href").get()

        if "<br>" in contact_name:
            contact_name = contact_name.split('<br>')[0].split('>')[-1]
        else:
            contact_name = ''

        city, country = parse_location(location)

        event = EventItem()

        event['name'] = name
        event['event_url'] = event_url
        event['description'] = desc

        # event['focus'] = scrapy.Field()
        # event['event_type'] = scrapy.Field()

        event['start'] = parse_date(start)
        event['end'] = parse_date(end)
        # event['length_in_days'] = scrapy.Field()

        event['country'] = country
        # event['state'] = scrapy.Field()
        event['city'] = city
        event['venue'] = html.unescape(venue.split('>')[-1])

        # event['price'] = scrapy.Field()
        # event['currency'] = scrapy.Field()

        # event['stand'] = scrapy.Field()
        # event['abstract'] = scrapy.Field()
        # event['talk'] = scrapy.Field()

        # event['ticket_deadline'] = scrapy.Field()
        # event['stand_deadline'] = scrapy.Field()
        # event['talk_deadline'] = scrapy.Field()

        event['contact_name'] = html.unescape(contact_name)
        event['contact_email'] = parse.unquote(contact_email).split(':')[-1]
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
