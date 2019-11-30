# -*- coding: utf-8 -*-

from collections import OrderedDict

from fr import util

# Scrapy settings for fr project
#
# For simplicity, this file contains only settings considered important or
# commonly used. You can find more settings consulting the documentation:
#
#     https://docs.scrapy.org/en/latest/topics/settings.html
#     https://docs.scrapy.org/en/latest/topics/downloader-middleware.html
#     https://docs.scrapy.org/en/latest/topics/spider-middleware.html

BOT_NAME = 'fr'

SPIDER_MODULES = ['fr.spiders']
NEWSPIDER_MODULE = 'fr.spiders'


# Crawl responsibly by identifying yourself (and your website) on the user-agent
# USER_AGENT = 'fr (+http://www.yourdomain.com)'

# Obey robots.txt rules
ROBOTSTXT_OBEY = True

# Configure maximum concurrent requests performed by Scrapy (default: 16)
# CONCURRENT_REQUESTS = 32

# Configure a delay for requests for the same website (default: 0)
# See https://docs.scrapy.org/en/latest/topics/settings.html#download-delay
# See also autothrottle settings and docs
# DOWNLOAD_DELAY = 3
# The download delay setting will honor only one of:
# CONCURRENT_REQUESTS_PER_DOMAIN = 16
# CONCURRENT_REQUESTS_PER_IP = 16

# Disable cookies (enabled by default)
# COOKIES_ENABLED = False
# COOKIES_DEBUG = True

# Disable Telnet Console (enabled by default)
# TELNETCONSOLE_ENABLED = False

# Override the default request headers:
CUSTOM_REQUEST_HEADERS = OrderedDict({
    'Host': 'www.infogreffe.com',
    'Connection': 'keep-alive',
    'Sec-Fetch-Mode': 'cors',
    'X-Requested-With': 'XMLHttpRequest',
    'User-Agent': 'scrapy',
    'Content-Type': 'application/x-www-form-urlencoded',
    'Accept': '*/*',
    'Sec-Fetch-Site': 'same-origin',
    'Referer': 'https://www.infogreffe.fr/',
    'Accept-Encoding': 'gzip, deflate, br',
    'Accept-Language': 'en-GB,en-US;q=0.9,en;q=0.8',
    'Cookie': ''
})

# Enable or disable spider middlewares
# See https://docs.scrapy.org/en/latest/topics/spider-middleware.html
SPIDER_MIDDLEWARES = {
    #    'fr.middlewares.FrSpiderMiddleware': 543,
    'fr.middlewares.SpiderExceptionMiddleware': 550,
}

# Enable or disable downloader middlewares
# See https://docs.scrapy.org/en/latest/topics/downloader-middleware.html
DOWNLOADER_MIDDLEWARES = {
    #    'fr.middlewares.FrDownloaderMiddleware': 543,
    # 'fr.middlewares.CustomHeadersMiddleware': 300,
    'scrapy.downloadermiddlewares.cookies.CookiesMiddleware': 300,
    'scrapy.contrib.downloadermiddleware.useragent.UserAgentMiddleware': None,
    'random_useragent.RandomUserAgentMiddleware': 400,
    # 'rotating_proxies.middlewares.RotatingProxyMiddleware': 610,
    # 'rotating_proxies.middlewares.BanDetectionMiddleware': 620,
}

# Setting for rotating User Agent
# User agents taken from https://github.com/tamimibrahim17/List-of-user-agents
USER_AGENT_BROWSERS = [
    'Chrome',
    'Android+Webkit+Browser',
    'Edge',
    'Firefox',
    'Internet+Explorer',
    'Opera',
    'Safari'
]
USER_AGENT_LIST = util.get_user_agent_list(USER_AGENT_BROWSERS)

# Settings for rotating proxy
# If the proxies would get used up too quickly, use proxy pools such:
# https://github.com/jhao104/proxy_pool
# https://github.com/Karmenzind/fp-server
PROXY_URL_SOURCES = [
    # Taken from https://github.com/clarketm/proxy-list
    "https://raw.githubusercontent.com/clarketm/proxy-list/master/proxy-list-raw.txt",
    # Taken from https://github.com/a2u/free-proxy-list
    "https://proxy.rudnkh.me/txt"
]
PROXY_FILE_SOURCES = []
ROTATING_PROXY_LIST = util.get_proxy_list(
    urls=PROXY_URL_SOURCES,
    files=PROXY_FILE_SOURCES
)

# Enable or disable extensions
# See https://docs.scrapy.org/en/latest/topics/extensions.html
# EXTENSIONS = {
#    'scrapy.extensions.telnet.TelnetConsole': None,
# }

# Configure item pipelines
# See https://docs.scrapy.org/en/latest/topics/item-pipeline.html
# ITEM_PIPELINES = {
#    'fr.pipelines.FrPipeline': 300,
# }

# Enable and configure the AutoThrottle extension (disabled by default)
# See https://docs.scrapy.org/en/latest/topics/autothrottle.html
AUTOTHROTTLE_ENABLED = True
# The initial download delay
# AUTOTHROTTLE_START_DELAY = 5
# The maximum download delay to be set in case of high latencies
AUTOTHROTTLE_MAX_DELAY = 120
# The average number of requests Scrapy should be sending in parallel to
# each remote server
AUTOTHROTTLE_TARGET_CONCURRENCY = 0.5
# Enable showing throttling stats for every response received:
# AUTOTHROTTLE_DEBUG = False

# Enable and configure HTTP caching (disabled by default)
# See https://docs.scrapy.org/en/latest/topics/downloader-middleware.html#httpcache-middleware-settings
# HTTPCACHE_ENABLED = True
# HTTPCACHE_EXPIRATION_SECS = 0
# HTTPCACHE_DIR = 'httpcache'
# HTTPCACHE_IGNORE_HTTP_CODES = []
# HTTPCACHE_STORAGE = 'scrapy.extensions.httpcache.FilesystemCacheStorage'
