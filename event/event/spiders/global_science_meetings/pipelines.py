# -*- coding: utf-8 -*-
'''
Global Science Meetings pipelines

Scrapy pipelines docs: https://docs.scrapy.org/en/latest/topics/item-pipeline.html
'''

import datetime
import json
import re

import scrapy.http

from event.items import EventItem
import event.util as util


class GlobalScienceMeetingsEventPipeline(object):

    def process_item(self, item, spider):

        def parseDate(datestring):
            if datestring.count('-') == 0:
                datestring = f'{datestring} - {datestring}'
            start, end = [s.strip() for s in datestring.split('-')]
            # Add year to the start date if missing
            if ',' not in start:
                start = f'{start}{end[ end.index(",") :]}'
            # Add month to the end date if missing
            if '.' not in end:
                end = f'{start[: start.index(".") + 2]}{end}'
            return [datetime.datetime.strptime(s, '%b. %d, %Y') for s in [start, end]]

        def parseDescription(desc):
            # Following regex catches all info even if multiple contact info is given, like the following
            # 'Contact Info: Christeena Jones | petrochemistrysummit@conferenceint.com | 44-203-7690-972 Contact Info: | | | Event Website'
            contact_infos = re.findall(
                r'Contact Info\:.*?\|.*?\|.*?(?=(?:\s*Contact Info)|\s*\|)', desc)
            if len(contact_infos) > 0:
                # Get the part that preceeds the contact info
                description = desc.split(contact_infos[0])[0]
            else:
                description = desc

            contacts = map(parseContactInfo, contact_infos)
            return description, contacts

        def parseContactInfo(info):
            name, email, number = [
                s.strip()
                for s in info.split('Contact Info: ')[1].split('|')
            ]
            return name, email, number

        row_index = item['meta']['row_index']
        res = scrapy.Selector(text=item['body'])

        row_selector = f'//table[@id="grdSQL"]//tr[descendant::a[contains(@href, "SysRowSelector${row_index}")]]'
        data_selector = '/td[@align]'
        data = res.xpath(f'{row_selector}{data_selector}').getall()
        text_data = [scrapy.Selector(text=d).xpath('//font/text()').get('').strip()
                     for d in data]

        description, contacts = parseDescription(text_data[5])
        names, emails, phones = [' '.join(l).strip() for l in zip(*contacts)]

        start, end = parseDate(text_data[2])

        event = EventItem()

        event['name'] = text_data[0]
        event['event_url'] = scrapy.Selector(text=data[5]
                                             ).xpath('//font/a/@href').get()
        event['description'] = re.sub(r'\n|\r', ' ', description)

        # event['focus'] = scrapy.Field()
        event['event_type'] = text_data[1].lower()

        event['start'] = start
        event['end'] = end
        # event['length_in_days'] = scrapy.Field()

        event['country'] = text_data[4]
        # event['state'] = scrapy.Field()
        event['city'] = text_data[3]
        # event['venue'] = scrapy.Field()

        # event['price'] = scrapy.Field()
        # event['currency'] = scrapy.Field()

        # event['stand'] = scrapy.Field()
        # event['abstract'] = scrapy.Field()
        # event['talk'] = scrapy.Field()

        # event['ticket_deadline'] = scrapy.Field()
        # event['stand_deadline'] = scrapy.Field()
        # event['talk_deadline'] = scrapy.Field()

        event['contact_name'] = names
        event['contact_email'] = emails
        event['contact_phone'] = phones

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
