# -*- coding: utf-8 -*-
'''
Labiotech pipelines

Scrapy pipelines docs: https://docs.scrapy.org/en/latest/topics/item-pipeline.html
'''


from event.pipelines import EventsCalendarPipeline


class LabiotechEventPipeline(EventsCalendarPipeline):
    pass
