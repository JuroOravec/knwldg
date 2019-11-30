# -*- coding: utf-8 -*-
'''
BioBasedPress pipelines

Scrapy pipelines docs: https://docs.scrapy.org/en/latest/topics/item-pipeline.html
'''

from event.pipelines import EventsCalendarPipeline


class BioBasedPressEventPipeline(EventsCalendarPipeline):

    def process_item(self, item, spider):
        event = super().process_item(item, spider)
        event['city'] = event['venue']
        del event['venue']
        return event
