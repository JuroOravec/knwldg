# -*- coding: utf-8 -*-
'''
Items models shared across the package

Scrapy item docs: https://docs.scrapy.org/en/latest/topics/items.html
'''


import scrapy


class ResponseItem(scrapy.Item):
    body = scrapy.Field()
    url = scrapy.Field()
    meta = scrapy.Field()


class EventItem(scrapy.Item):
    name = scrapy.Field()
    id = scrapy.Field()

    event_url = scrapy.Field()
    description = scrapy.Field()
    focus = scrapy.Field()
    event_type = scrapy.Field()

    start = scrapy.Field()
    end = scrapy.Field()
    length_in_days = scrapy.Field()

    country = scrapy.Field()
    state = scrapy.Field()
    city = scrapy.Field()
    venue = scrapy.Field()

    price = scrapy.Field()
    currency = scrapy.Field()

    stand = scrapy.Field()
    abstract = scrapy.Field()
    talk = scrapy.Field()

    ticket_deadline = scrapy.Field()
    stand_deadline = scrapy.Field()
    talk_deadline = scrapy.Field()

    contact_name = scrapy.Field()
    contact_email = scrapy.Field()
    contact_phone = scrapy.Field()

    organizer = scrapy.Field()
    organizer_url = scrapy.Field()

    newsletter = scrapy.Field()
    twitter = scrapy.Field()
    facebook = scrapy.Field()
    linkedin = scrapy.Field()
    instagram = scrapy.Field()

    hashtags = scrapy.Field()

    relevant_to_bio = scrapy.Field()
    relevant_to_ind_bio = scrapy.Field()

    ignore = scrapy.Field()
    source = scrapy.Field()
    notes = scrapy.Field()
