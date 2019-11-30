# -*- coding: utf-8 -*-
'''
Swiss Biotech pipelines

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


class SwissBiotechEventPipeline(object):
    def process_item(self, item: ResponseItem, spider):

        def parse_date(datestring):
            if datestring is None:
                return None
            ds = datestring.strip()
            return datetime.datetime.strptime(ds, '%B %d, %Y')

        def parse_location(loc):
            # location is in form of
            # 'StreetName No, Postcode City, Country'
            # But there is no clear distinction between which words belong to city
            # and which to postcode, so we assume that postcode is only 1 word long
            addr = loc.split(',')
            country = addr[-1]
            city = addr[-2] if len(addr) > 1 else ''
            return city, country

        def get_infobox(sel, title=None):
            # Select div.pf-body if the preceding div.pf-head has descendant h5 with specific text
            # If title is None, matches h5 with no text instead
            #
            # '''
            # div.pf-head
            #   ...
            #   h5 {title}
            # div.pf-body
            # '''
            text_sel = f'text()="{title}"' if title is not None else 'not(text())'
            return sel.xpath(f'.//div[@class="pf-body" and preceding-sibling::div[@class="pf-head"]//h5[{text_sel}]]')

        def get_icon_text_by_class(sel, classes):
            # Select span if the preceding i has specific classes
            #
            # '''
            # i.{cls}
            # span *Desired text here*
            # '''
            return sel.xpath(f'.//span[preceding-sibling::i[{xpath_class(classes)}]]/text()').getall()

        res = scrapy.Selector(text=item['body'])

        name = res.xpath(
            f"//h1[contains(@class, '-primary-text')]/text()").get('')
        event_url = res.xpath(
            "//a[descendant-or-self::span[text()='Website']]/@href").get('')
        desc = scrapy.Selector(text=get_infobox(res, None).get('')).xpath(
            'normalize-space(string((.//div)[1]))').get('')

        details = get_infobox(res, 'Details')
        start = get_icon_text_by_class(details, ['fa-calendar'])
        end = get_icon_text_by_class(details, ['fa-arrow-right'])
        location = get_icon_text_by_class(details, ['icon-location-pin-add-2'])

        org_details = get_infobox(res, 'Hosted by')
        organizer = org_details.xpath(
            f".//span[{xpath_class(['host-name'])}]/text()").get()
        organizer_url = org_details.xpath(
            f".//div[{xpath_class(['event-host'])}]/a/@href").get()

        event_details = get_infobox(res, 'Type of event')
        types = get_icon_text_by_class(event_details, ['bookmark_border'])

        if organizer is None:
            organizer = item['meta']['organizer']

        city, country = parse_location(location[-1])

        event = EventItem()

        event['name'] = name
        event['event_url'] = event_url
        event['description'] = desc

        # event['focus'] = scrapy.Field()
        event['event_type'] = types[0] if len(types) else ''

        event['start'] = parse_date(start[0].split('@')[0])
        event['end'] = parse_date(end[0]) if len(end) else None
        # event['length_in_days'] = scrapy.Field()

        event['country'] = country
        # event['state'] = scrapy.Field()
        event['city'] = city
        # event['venue'] = html.unescape(venue.split('>')[-1])

        # event['price'] = scrapy.Field()
        # event['currency'] = scrapy.Field()

        # event['stand'] = scrapy.Field()
        # event['abstract'] = scrapy.Field()
        # event['talk'] = scrapy.Field()

        # event['ticket_deadline'] = scrapy.Field()
        # event['stand_deadline'] = scrapy.Field()
        # event['talk_deadline'] = scrapy.Field()

        # event['contact_name'] = html.unescape(contact_name)
        # event['contact_email'] = parse.unquote(contact_email).split(':')[-1]
        # event['contact_phone'] = scrapy.Field()

        event['organizer'] = organizer
        event['organizer_url'] = organizer_url

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
