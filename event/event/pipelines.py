# -*- coding: utf-8 -*-
'''
Pipelines shared across the package

Scrapy pipelines docs: https://docs.scrapy.org/en/latest/topics/item-pipeline.html
'''

import datetime
import re

import scrapy.http
import pycountry

from event.items import EventItem, ResponseItem
import event.util as util
from common.util import xpath_class, is_url, unpack_url, pack_url


class EventsCalendarPipeline(object):
    '''
    Pipeline for spiders that scrape WP sites that use
    The Events Calendar by Modern Tribe (https://theeventscalendar.com/)
    '''

    def process_item(self, item: ResponseItem, spider):

        def parseDate(datestring):
            if datestring is None:
                return None
            return datetime.datetime.strptime(datestring, '%Y-%m-%d')

        res = scrapy.Selector(text=item['body'])

        name = res.xpath(
            f"//h1[{xpath_class(['tribe-events-single-event-title'])}]/text()").get()
        desc = res.xpath(
            f"normalize-space(string(//div[{xpath_class(['tribe-events-content'])}]))").get()
        start = res.xpath(
            f"//abbr[{xpath_class(['tribe-events-start-date', 'tribe-events-start-datetime'])}]/@title").get()
        end = res.xpath(
            f"//abbr[{xpath_class(['tribe-events-end-date', 'tribe-events-end-datetime'])}]/@title").get()
        event_type = res.xpath(
            f"//dd[{xpath_class(['tribe-events-event-categories'])}]/a/text()").get('')
        event_url = res.xpath(
            f"//dd[{xpath_class(['tribe-events-event-url'])}]/a/@href").get()
        organizer = res.xpath(
            f"//dd[{xpath_class(['tribe-organizer'])}]/text()").get('')
        organizer_url = res.xpath(
            f"//dd[{xpath_class(['tribe-organizer-url'])}]/a/@href").get('')
        venue = res.xpath(
            f"//dd[{xpath_class(['tribe-venue'])}]/text()").get('')
        city = res.xpath(
            f"//span[{xpath_class(['tribe-locality'])}]/text()").get('')
        state = res.xpath(
            f"//abbr[{xpath_class(['tribe-region'])}]/@title").get('')
        country = res.xpath(
            f"//span[{xpath_class(['tribe-country-name'])}]/text()").get('')
        email = res.xpath(
            f"//dd[{xpath_class(['tribe-organizer-email'])}]/text()").get('')

        event = EventItem()

        event['name'] = name.strip()
        event['event_url'] = event_url.strip()
        event['description'] = desc.strip()

        # event['focus'] = scrapy.Field()
        event['event_type'] = event_type.lower().strip()

        event['start'] = parseDate(start)
        event['end'] = parseDate(end)
        # event['length_in_days'] = scrapy.Field()

        event['country'] = country.strip()
        event['state'] = state.strip()
        event['city'] = city.strip()
        event['venue'] = venue.strip()

        # event['price'] = scrapy.Field()
        # event['currency'] = scrapy.Field()

        # event['stand'] = scrapy.Field()
        # event['abstract'] = scrapy.Field()
        # event['talk'] = scrapy.Field()

        # event['ticket_deadline'] = scrapy.Field()
        # event['stand_deadline'] = scrapy.Field()
        # event['talk_deadline'] = scrapy.Field()

        # event['contact_name'] = scrapy.Field()
        event['contact_email'] = email.strip()
        # event['contact_phone'] = scrapy.Field()

        event['organizer'] = organizer.strip()
        event['organizer_url'] = organizer_url.strip()

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


class EventTypePipeline(object):
    '''
    Pipeline which tries to guess event type based on event's name
    '''

    def process_item(self, item, spider):
        try:
            name = item['name']
            desc = item.get('description', '')
            event_type = item.get('event_type', '')
        except (TypeError, AttributeError):
            spider.logger.warning('Item is not an event object, skipping '
                                  'EventTypePipeline')
            return item

        name = name.lower()
        if event_type != '' and event_type is not None:
            item['event_type'] = item['event_type'].lower()
            return item

        event_types = ('conference summit forum symposium expo congress '
                       'seminar workshop course').split()

        # search for event typec in name
        for event in event_types:
            if event in name:
                item['event_type'] = event
                return item

        # search for event typec in desc
        if desc == '':
            return item
        for event in event_types:
            if event in desc:
                item['event_type'] = event
                break

        return item


class EventLocationPipeline(object):
    '''
    Pipeline which tries to normalize country and state names of event objects
    '''

    def process_item(self, item, spider):
        try:
            country = item.get('country', '')
            state = item.get('state', '')
        except AttributeError:
            spider.logger.warning('Item is not an event object, skipping '
                                  'EventLocationPipeline')
            return item

        country = '' if country is None else country.lower()
        state = '' if state is None else state.lower()

        # country lookup is available for 2- and 3-letter codes
        matched_country = None
        if country != '' and len(country) <= 3:
            try:
                matched_country = pycountry.countries.lookup(country)
                item['country'] = matched_country.name
            except LookupError:
                item['country'] = item['country'].capitalize()

            # state lookup is available only for codes in the form "CC-SS" where
            # - CC is 2-letter country code
            # - SS is 2-letter state code
        if len(state) == 2 or (len(state) == 5 and '-' in state):
            # include the matched country code in the searched query
            if len(state) == 2 and matched_country is not None:
                state_q = state if '-' in state else f'{matched_country.code}-{state}'
            else:
                state_q = state

            try:
                item['state'] = pycountry.subdivisions.lookup(state_q).name
            except LookupError:
                item['state'] = item['state'].capitalize()

        return item


class EventDatePipeline(object):
    '''
    Pipeline which tries to normalize dates of event objects
    '''

    def process_item(self, item, spider):
        try:
            start = item.get('start')
            end = item.get('end')
            ticket_deadline = item.get('ticket_deadline')
            stand_deadline = item.get('stand_deadline')
            talk_deadline = item.get('talk_deadline')
        except AttributeError:
            spider.logger.warning('Item is not an event object, skipping '
                                  'EventDatePipeline')
            return item

        if start is not None and not isinstance(start, str):
            item['start'] = util.formatDate(start)
        if not isinstance(end, str):
            end = start if end is None else end
            item['end'] = util.formatDate(end)
        if not isinstance(end, str) and not isinstance(start, str):
            item['length_in_days'] = util.dateDuration(start, end)

        if ticket_deadline is not None and not isinstance(ticket_deadline, str):
            item['ticket_deadline'] = util.formatDate(ticket_deadline)
        if stand_deadline is not None and not isinstance(stand_deadline, str):
            item['stand_deadline'] = util.formatDate(stand_deadline)
        if talk_deadline is not None and not isinstance(talk_deadline, str):
            item['talk_deadline'] = util.formatDate(talk_deadline)

        return item


class EventMetadataPipeline(object):
    '''
    Pipeline which adds metadata to event objects
    '''

    def process_item(self, item, spider):
        try:
            source = item.get('source')
            id = item.get('id')
        except AttributeError:
            spider.logger.warning('Item is not an event object, skipping '
                                  'EventMetadataPipeline')
            return item

        item['source'] = source if source is not None else spider.source
        item['id'] = id if id is not None else util.event_id(item)

        return item


class UrlCleanerPipeline(object):
    '''
    For each URL string value of item, cleans the URL of tracking query params
    '''

    def process_item(self, item, spider):
        try:
            for k in item:
                if isinstance(item[k], str) and is_url(item[k]):
                    url_obj, q_obj = unpack_url(item[k])
                    q_obj_copy = {}
                    for q_k in q_obj:
                        if not q_k.startswith('utm'):
                            q_obj_copy[q_k] = q_obj[q_k]
                    item[k] = pack_url(url_obj, q_obj_copy)
        except LookupError:
            spider.logger.warning('Item is not an object, skipping '
                                  'UrlCleanerPipeline')
        return item


class StripperPipeline(object):
    '''
    Performs str.strip() on all string dictionary values
    '''

    def process_item(self, item, spider):
        try:
            for k in item:
                if isinstance(item[k], str):
                    item[k] = item[k].strip()
        except LookupError:
            spider.logger.warning('Item is not an object, skipping '
                                  'StripperPipeline')
        return item


class WhitespaceNormalizerPipeline(object):
    '''
    Normalizes all whitespace to a single space (` `) on all string dictionary values
    '''

    def process_item(self, item, spider):
        try:
            for k in item:
                if isinstance(item[k], str):
                    item[k] = re.sub(r'\n|\r', ' ', item[k].strip())
        except LookupError:
            spider.logger.warning('Item is not an object, skipping '
                                  'WhitespaceNormalizerPipeline')
        return item
