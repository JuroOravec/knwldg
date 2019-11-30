
import scrapy

import common.components as components


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
