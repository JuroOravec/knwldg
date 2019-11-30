# -*- coding: utf-8 -*-
'''
Solebury Trout pipelines

Scrapy pipelines docs: https://docs.scrapy.org/en/latest/topics/item-pipeline.html
'''

import datetime

import scrapy.http

from event.items import EventItem
import event.util as util


class SoleburyTroutEventPipeline(object):

    def process_item(self, item, spider):

        def parseDate(datestring):
            m_name, d, y = datestring.replace(',', '').split()
            m = datetime.datetime.strptime(m_name, '%B').month
            d, m, y = map(int, [d, m, y])
            return datetime.datetime(y, m, d)

        event = EventItem()

        event['name'] = item['Event']
        event['event_url'] = item['Website']
        event['description'] = item['Description']

        # focus = scrapy.Field()
        # event_type = scrapy.Field()

        event['start'] = parseDate(item['Start'])
        event['end'] = parseDate(item['End'])
        # event['length_in_days'] = scrapy.Field()

        loc = item['Location'].split(', ')
        event['country'] = loc[-1]
        event['state'] = loc[1] if len(loc) > 2 else None
        event['city'] = loc[0]
        # venue = scrapy.Field()

        # price = scrapy.Field()
        # currency = scrapy.Field()

        # stand = scrapy.Field()
        # abstract = scrapy.Field()
        # talk = scrapy.Field()

        # ticket_deadline = scrapy.Field()
        # stand_deadline = scrapy.Field()
        # talk_deadline = scrapy.Field()

        # contact_name = scrapy.Field()
        # contact_email = scrapy.Field()
        # contact_phone = scrapy.Field()

        # organizer = scrapy.Field()
        # organizer_url = scrapy.Field()

        # newsletter = scrapy.Field()
        # twitter = scrapy.Field()
        # facebook = scrapy.Field()
        # linkedin = scrapy.Field()
        # instagram = scrapy.Field()

        # hashtags = scrapy.Field()

        # relevant_to_bio = scrapy.Field()
        # relevant_to_ind_bio = scrapy.Field()

        # ignore = scrapy.Field()
        # notes = scrapy.Field()

        # event['source'] = scrapy.Field()
        # event['id'] = scrapy.Field()

        return event
