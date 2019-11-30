# -*- coding: utf-8 -*-
'''
IBioIC pipelines

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


class IBioICEventPipeline(object):
    def process_item(self, item: ResponseItem, spider):

        def parse_date(datestring):
            # parses dates in format:
            # DD MMM YYYY HH:MM AM/PM
            # DayOfWeek DD Month YYYY
            # DD Month YYYY
            # DD-DD Month YYYY

            def _parse_date(s):
                s_ = s.strip()
                try:
                    return datetime.datetime.strptime(s_, '%d %B %Y')
                except ValueError:
                    pass
                return datetime.datetime.strptime(s_, '%d %b %Y')

            if datestring is None:
                return None
            ds = datestring.strip()

            # Dates at this stage:
            #   25 Jun 2019 1: 00 PM
            #   Wednesday 26 June 2019
            #   25 - 28 February 2020

            # Strip DayOfWeek detail if it's at the beginning
            if ds[0].isalpha():
                ds = ds.split(' ', 1)[-1]

            # Dates at this stage:
            #   25 Jun 2019 1: 00 PM
            #   26 June 2019
            #   25 - 28 February 2020

            # Strip hour details if it's there
            if ds.count(':') > 0:
                ds = ds.split(':')[0].rsplit(' ', 1)[0]

            # Dates at this stage:
            #   25 Jun 2019
            #   26 June 2019
            #   25 - 28 February 2020

            # Normalize date range if it's 1-day event
            if ds.count('-') == 0:
                ds = f'{ds} - {ds}'

            # Dates at this stage:
            #   25 Jun 2019 - 25 Jun 2019
            #   26 June 2019 - 26 June 2019
            #   25 - 28 February 2020

            # Normalize `25 - 28 February 2020` to `25 February 2020 - 28 February 2020`
            if len(ds.split('-')[0].strip().split()) == 1:
                d, mo__yr = ds.split('-')[-1].strip().split(' ', 1)
                ds = f'{d} {mo__yr} - {ds.split("-")[-1].strip()}'

            # Dates at this stage:
            #   25 Jun 2019 - 25 Jun 2019
            #   26 June 2019 - 26 June 2019
            #   25 February 2020 - 28 February 2020

            start, end = [_parse_date(s) for s in ds.split('-')]
            return start, end

        def parse_price(pricestring):
            # parses prices in format:
            # 'bla bla PP.PP bla bla'
            if pricestring is None:
                return None
            price = re.search(r'\d[0-9 ,.]*', pricestring)
            if price is not None:
                return price.group().strip()

        res = scrapy.Selector(text=item['body'])

        name = res.xpath(f"(//h3)[1]/span/strong/text()").get()
        desc = res.xpath(
            f"normalize-space(string(//div[{xpath_class(['wysiwygcontent'])}]))").get('')
        venue = res.xpath(
            f'string(//div[@id="event-details"]/ul/li[label[text()="Event Location:"]])').get('')
        reg_deadline = res.xpath(
            f'string(//div[@id="event-details"]/ul/li[label[text()="Registrations Close:"]])').get()
        price = res.xpath(
            f'string(//div[@id="event-details"]/ul/li[label[text()="Your Price:"]])').get()
        date = res.xpath(
            f'string(//div[@id="event-details"]/ul/li[label[text()="Date:"]])').get('-')

        venue, reg_deadline, price, date = [
            s.split(':', 1)[-1].strip() if s is not None else None
            for s in [venue, reg_deadline, price, date]
        ]

        start, end = parse_date(date)
        _, ticket_deadline = parse_date(reg_deadline)

        event = EventItem()

        event['name'] = name
        event['event_url'] = item['url']
        event['description'] = desc

        # event['focus'] = scrapy.Field()
        # event['event_type'] = scrapy.Field()

        event['start'] = start
        event['end'] = end
        # event['length_in_days'] = scrapy.Field()

        event['country'] = 'Australia'
        # event['state'] = scrapy.Field()
        event['city'] = ''
        event['venue'] = venue

        event['price'] = parse_price(price)
        event['currency'] = 'AUD'

        # event['stand'] = scrapy.Field()
        # event['abstract'] = scrapy.Field()
        # event['talk'] = scrapy.Field()

        event['ticket_deadline'] = ticket_deadline
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
