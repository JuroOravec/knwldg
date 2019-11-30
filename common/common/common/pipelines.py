import csv

import scrapy

import common.util as util

class CsvWriterPipeline(object):

    def open_spider(self, spider):
        timestamp = spider._time_tag if hasattr(spider, '_time_tag') else util.time_tag()
        self.file = open(
            f'data/{spider.name}__{timestamp}.csv', 'w', newline='')
        # if python < 3 use
        #self.file = open('mietwohnungen.csv', 'wb')
        self.items = []
        self.colnames = []

    def close_spider(self, spider):
        csvWriter = csv.DictWriter(
            self.file, fieldnames=self.colnames)  # , delimiter=',')
        spider.logger.info("HEADER: " + str(self.colnames))
        csvWriter.writeheader()
        for item in self.items:
            csvWriter.writerow(item)
        self.file.close()

    def process_item(self, item, spider):
        # add the new fields
        for f in item.keys():
            if f not in self.colnames:
                self.colnames.append(f)

        # add the item itself to the list
        self.items.append(item)
        return item