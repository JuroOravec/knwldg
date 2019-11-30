# -*- coding: utf-8 -*-

# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html


import logging


class TemplatePipeline(object):

    def open_spider(self, spider):
        # logging.info("Template message")
        pass

    def close_spider(self, spider):
        # logging.info("Template message")
        pass

    def process_item(self, item, spider):
        # logging.info("Template message")
        return item
