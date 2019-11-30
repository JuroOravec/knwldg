
import scrapy

import common.components as components
from common.composer import Composer


class BaseSpider(scrapy.Spider, components.TimeTaggedMixin):
    '''Base class with common behavior for other spiders'''

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class YourFavouriteSpider(BaseSpider,
                          components.ComposableSpiderMixin):
    '''
    Template Spider
    '''

    name = "YourFavouriteSpider"

    def start_requests(self):
        yield


class CompositeSpider(components.ComposableSpiderMixin):
    '''
    Composite class combining the whole workflow of multiple spiders
    into a single spider.
    '''

    name = "composite_spider"

    class SubSpiderOne(components.SubclassMixin):
        pass

    SubSpiderTwo = YourFavouriteSpider
    SubSpiderThree = YourFavouriteSpider

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._one_spider = self.SubSpiderOne(
            context=self, *args, **kwargs)
        self._two_spider = self.SubSpiderTwo(
            context=self, *args, **kwargs)
        self._three_spider = self.SubSpiderThree(*args, **kwargs)

    def start_requests(self):
        return

    def parse(self, response):
        return response


class SpiderOne(scrapy.Spider):
    name = "spider_one"

    count = 0
    start_urls = [
        f'https://www.{i}.com' for i in ['test', 'example']]

    def parse(self, response):
        print("SpiderOne.parse triggered - OK!")
        if self.count < 3:
            self.count += 1
            return scrapy.Request(url=f'{response.url}#appended', meta=response.meta, dont_filter=True)


class SpiderTwo(scrapy.Spider):
    name = "spider_two"

    def start_requests(self):
        print("SpiderTwo.start_requests triggered - Oops!")
        return scrapy.Request("http://www.wrong.com")

    def parse(self, response):
        print("SpiderTwo.parse triggered - OK!")
        return scrapy.Request(url=f'{response.url}#hello_from_2', meta=response.meta, dont_filter=True)


class Composite(Composer):

    name = 'spider_one_two'

    spiders = {
        'common.spiders.SpiderOne': [1, 3],
        'common.spiders.SpiderTwo': 2,
    }
