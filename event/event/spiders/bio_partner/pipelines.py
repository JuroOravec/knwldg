# -*- coding: utf-8 -*-
'''
Bio Partner pipelines

Scrapy pipelines docs: https://docs.scrapy.org/en/latest/topics/item-pipeline.html
'''

import datetime

import scrapy

from event.items import EventItem, ResponseItem


class BioPartnerEventPipeline(object):
    def process_item(self, item: ResponseItem, spider):

        def parse_date(datestring, pattern):
            if datestring is None:
                return None
            ds = datestring.strip()
            return datetime.datetime.strptime(ds, pattern)

        def parse_info(info):
            if info is not None and info != '':
                return scrapy.Selector(text=info).xpath(
                    'normalize-space(string(//*))').get()
            return ''

        res = item['body']

        intro, desc, info = [parse_info(res[key]) for key in [
            'introduction', 'description', 'other_information']]

        tckt_deadline = None
        if res['last_registration_date'] is not None and res['last_registration_date'] != '':
            tckt_deadline = parse_date(
                res['last_registration_date'], '%d %b %Y')

        event = EventItem()

        event['name'] = res['title']
        event['event_url'] = res['webpage'] or res['registration_link']
        event['description'] = f"{intro}\n{desc}\n{info}"

        event['focus'] = res['scientific_focus_text']
        event['event_type'] = res['classification'].split('/')[0]

        event['start'] = parse_date(res['start_date'], '%Y-%m-%d')
        event['end'] = parse_date(res['end_date'], '%Y-%m-%d')
        # event['length_in_days'] = scrapy.Field()

        event['country'] = res['country'] or res['location_country']
        event['state'] = res['location_state']
        event['city'] = res['city'] or res['location_city']
        event['venue'] = res['location']

        # event['price'] = scrapy.Field()
        # event['currency'] = scrapy.Field()

        # event['stand'] = scrapy.Field()
        # event['abstract'] = scrapy.Field()
        # event['talk'] = scrapy.Field()

        event['ticket_deadline'] = tckt_deadline
        # event['stand_deadline'] = scrapy.Field()
        # event['talk_deadline'] = scrapy.Field()

        event['contact_name'] = res['external_contact_name']
        event['contact_email'] = res['external_contact_email']
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
