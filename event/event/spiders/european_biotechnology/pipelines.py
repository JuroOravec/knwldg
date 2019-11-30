# -*- coding: utf-8 -*-
'''
European Biotechnology pipelines

Scrapy pipelines docs: https://docs.scrapy.org/en/latest/topics/item-pipeline.html
'''

import datetime
import re

import scrapy

from event.items import EventItem, ResponseItem
from common.util import xpath_class, lot2dol, flatten, lmap


class EuropeanBiotechnologyEventPipeline(object):
    def process_item(self, item: ResponseItem, spider):

        def parse_date(datestring):
            if datestring is None:
                return None
            ds = datestring.replace('-', '').strip()
            return datetime.datetime.strptime(ds, '%d.%m.%Y')

        def parse_description(desc):
            # Following regexes catches all info even if multiple contact info is given, like the following
            # 'Phone: +49-89-949-203-81, Fax: +49-89-949-203-89, eMail: info@analytica.de'
            contact_infos = re.findall(
                r'(?:eMail|Phone|Fax):\s*.*?(?=,|\n|$)', desc)
            # 'Info: Green Power Conferences, Robert Wilson'
            contact_names = re.findall(
                r'(?<=Info:\s).*?(?=\n|$|eMail|Phone|Fax)', desc)
            if len(contact_names) > 0:
                # Get the part that preceeds the contact info
                description = desc.split(contact_names[0])[0]
            else:
                description = desc

            contact_details = lmap(parse_contact_info, contact_infos)
            contact_details.extend(
                flatten(
                    lmap(parse_contact_names, contact_names)
                )
            )
            contacts = lot2dol(contact_details)
            return description, contacts

        def parse_contact_info(info):
            contact_type, contact_detail = [
                re.sub(r'\s*', '', s.lower())
                for s in info.split(':')
            ]
            return contact_type, contact_detail

        def parse_contact_names(info):
            contact_names = [s.strip() for s in info.split(',')]
            try:
                organizer = contact_names.pop(0)
            except IndexError:
                organizer = ''

            return [
                ('organizer', organizer),
                *[('name', n) for n in contact_names]
            ]

        def parse_location(loc):
            # if there are parentheses, they hold the code of the country
            # 'Basel (CH)'
            if '(' in loc:
                city, country = map(
                    str.strip,
                    filter(None, re.split(r'\((?:.*?)\)', loc))
                )
            else:
                city = loc
                country = None
            return city, country

        res = scrapy.Selector(text=item['body'])

        name = res.xpath(
            f"//div[{xpath_class(['ce-inner-headline'])}]//span/text()").get()
        desc = res.xpath(
            f"normalize-space(string(//div[{xpath_class(['ce-inner-text'])}]/p))").get()
        start = res.xpath(
            f"//span[{xpath_class(['event-date'])} and position()=1]/text()").get()
        end = res.xpath(
            f"//span[{xpath_class(['event-date'])} and position()=2]/text()").get()
        event_url = res.xpath(
            f"//div[{xpath_class(['ce-inner-url'])}]/a/@href").get()
        city = res.xpath(
            f"//span[{xpath_class(['event-location'])}]/text()").get('')

        description, contacts = parse_description(desc)
        emails = ' '.join(contacts.get('email', []))
        phones = ' '.join(contacts.get('phone', []))
        names = ' '.join(contacts.get('name', []))
        organizer = ' '.join(contacts.get('organizer', []))

        city, country = parse_location(city)

        event = EventItem()

        event['name'] = name
        event['event_url'] = event_url
        event['description'] = description

        # event['focus'] = scrapy.Field()
        # event['event_type'] = scrapy.Field()

        event['start'] = parse_date(start)
        event['end'] = parse_date(end)
        # event['length_in_days'] = scrapy.Field()

        event['country'] = country
        # event['state'] = scrapy.Field()
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

        event['contact_name'] = names
        event['contact_email'] = emails
        event['contact_phone'] = phones

        event['organizer'] = organizer
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
