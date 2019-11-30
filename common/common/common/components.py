from abc import ABCMeta, abstractmethod
import dataclasses
import functools
import inspect
import importlib
import importlib.util
import logging
from pathlib import Path
import traceback as tb

# from browsermobproxy import Server
import scrapy.utils.conf as sconf
import scrapy
import selenium.webdriver
from selenium.webdriver.remote.remote_connection import LOGGER as selenium_logger
import six

import common.util as util

if six.PY2:
    from ConfigParser import SafeConfigParser as ConfigParser
else:
    from configparser import ConfigParser


class StringCombinationsMixin():
    '''Interface for passing settings for `string_combinations` to the class instance'''

    @dataclasses.dataclass
    class StringCombinations:
        start = None
        end = None
        pattern = None
        valid_chars = 'abcdefghijklmnopqrstuvwxyz0123456789'
        variants = None
        min_length = 1

        @functools.wraps(util.string_combinations)
        def generate(self, seed=""):
            return util.string_combinations(
                seed=seed,
                start=self.start,
                end=self.end,
                pattern=self.pattern,
                valid_chars=self.valid_chars,
                variants=self.variants,
                min_length=self.min_length
            )

    def __init__(self, start=None, end=None, pattern=None, valid_chars=None, variants=None, min_length=None, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.string_combinations = self.StringCombinations()

        if start:
            self.string_combinations.start = start
        if end:
            self.string_combinations.end = end
        if pattern:
            self.string_combinations.pattern = pattern
        if valid_chars:
            self.string_combinations.valid_chars = valid_chars
        if variants:
            self.string_combinations.variants = variants
        if min_length:
            self.string_combinations.min_length = min_length


class LimitedResultsResolver(metaclass=ABCMeta):
    '''
    Interface for handling scraping of websites where search results have
    an upper limit on the number of returned entries. 

    Strategy promoted by this class is to detect when the upper limit was
    overstepped and repeat the search with more specific parameters in such 
    case.
    '''

    @abstractmethod
    def resolve_result_limit(self, response):
        ...

    @abstractmethod
    def is_result_limited(self, *args, **kwargs):
        ...


class LimitedResultsByQueryResolverMixin(
    StringCombinationsMixin,
    LimitedResultsResolver,
    ):
    '''
    Mixin handling scraping of websites where search results have
    an upper limit on the number of returned entries and the search parameters
    are passed as URL query parameters.
    '''

    @property
    @abstractmethod
    def query_param(self):
        ...

    @abstractmethod
    def get_new_queries(self, query):
        ...

    def resolve_result_limit(self, response):
        url_obj, q_obj = util.unpack_url(response.url)
        old_query = q_obj[self.query_param]
        for query in self.get_new_queries(q_obj):
            if query == old_query:
                continue
            q = q_obj.copy()
            q[self.query_param] = query
            yield (util.pack_url(url_obj, q), url_obj, q)


class LimitedResultsByQueryNameResolverMixin(
    LimitedResultsByQueryResolverMixin
   ):
    '''
    Mixin for a specific case of LimitedResultsByQueryResolverMixin where
    only the search name is the parameter that is changed to alleviate
    the search results limit.

    This is often a sufficient solution for most of the website where entries
    are searched for and number of results is limited

    Mixin uses following variables:

    - `query_param` - string that identifies the query parameter of the 
                      searched term.
    '''

    query_param = None

    def __init__(self, query_param=None, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if query_param is not None:
            self.query_param = query_param
        elif self.query_param is None:
            raise TypeError('LimitedResultsByQueryNameResolverMixin is '
                            "missing keyword argument 'query_param' ")

    def get_new_queries(self, query):
        old_query = query.get(self.query_param)
        next_query_length = max(
            self.string_combinations.min_length,
            len(old_query) + 1
        )
        self.string_combinations.min_length = next_query_length
        new_queries = self.string_combinations.generate(seed=old_query)
        return new_queries


class ComposableSpiderMixin(scrapy.Spider):
    '''
    Mixin decoupling response processing and flow control,
    enabling redirection of outgoing requests or results.
    '''

    def parse(self, response):
        return self.resolve_output([response])

    def resolve_output(self, results):
        return iter(results)


class SCSpider2SpiderMixin(ComposableSpiderMixin):
    '''
    Mixin for directing yielded requests from one spider to another
    in the Scrapy Cluster framework
    '''

    @property
    @abstractmethod
    def next_spider(self):
        ...

    def resolve_output(self, requests):
        for req in requests:
            req.meta['spiderid'] = self.next_spider
            yield req


class TimeTaggedMixin():

    def __init__(self, *args, **kwargs):
        self._time_tag = util.time_tag()
        super().__init__(*args, **kwargs)


class AncestorSettingSpiderMixin(scrapy.Spider):
    '''
    Allow spiders to load settings from ancestors.

    For each ancestor, the settings are loaded in following order:
    - project's settings.py, 
    - local settings.py (if spider inherits from LocalSettingsSpiderMixin)
    - custom_settings attribute

    Import of a specific type of settings is controlled with boolean attributes
    `_load_custom_settings`, `_load_local_settings_file`, and `_load_settings_file`
    (default `True` for all).

    By default, settings are applied down the inheritance tree (ancestors loaded
    first). Order can be overriden by overriding the class method `_get_ancestors`.

    Note: Parent settings modifications are applied after this mixin.
    '''

    _load_custom_settings = True
    _load_local_settings_file = True
    _load_settings_file = True

    @classmethod
    def update_settings(cls, settings):
        logger = logging.getLogger(getattr(cls, "name") or __name__)

        settings_cp = settings.copy_to_dict()
        ancestors = cls._get_ancestors()
        logger.debug('Ancestors found for spider "{}": {}'.format(
            cls.__name__, [getattr(a, '__name__') for a in ancestors]))

        for i, anc in enumerate(ancestors):

            if cls._load_settings_file:
                anc_sttngs_mdl = cls._settings_from_spider(anc)
                if anc_sttngs_mdl is not None:
                    util.soft_update(settings_cp, vars(anc_sttngs_mdl),
                                     dict_mode='update')
                    logger.info('Loaded settings file from ancestor "{}" to "{}"'.format(
                        anc.__name__, cls.__name__))

            if cls._load_local_settings_file and issubclass(cls, LocalSettingsSpiderMixin):
                anc_lcl_sttngs_mdl = LocalSettingsSpiderMixin._get_local_settings(
                    anc)
                if anc_lcl_sttngs_mdl is not None:
                    util.soft_update(settings_cp, vars(anc_lcl_sttngs_mdl),
                                     dict_mode='update')
                    logger.info('Loaded local settings file from ancestor "{}" to "{}"'.format(
                        anc.__name__, cls.__name__))

            if cls._load_custom_settings:
                if anc.custom_settings is not None:
                    util.soft_update(settings_cp, anc.custom_settings,
                                     dict_mode='update')
                    logger.info('Loaded custom settings from ancestor "{}" to "{}"'.format(
                        anc.__name__, cls.__name__))

        settings.setdict(settings_cp)

        # lastly hand over to super so fresher modifications can be applied
        super().update_settings(settings)

    @classmethod
    def _settings_from_spider(cls, sp):
        logger = logging.getLogger(getattr(cls, "name") or __name__)
        # Given a class, workflow is following:
        # 1) get path to the file
        # 2) get global config locations from sconf.get_sources(False)
        # 3) search all of these for config files using sconf.closest_scrapy_cfg
        # 4) pass config filepaths to ConfigParser, with local overriding global
        # 5) search settings section of parsed config, looking for entry
        #    whose name matches the name of the package of the class, or 'default'
        #    entry if no other was found. This defines the module import path.
        # 6) Import the module

        spcls = sp if inspect.isclass(sp) else sp.__class__
        spcls_name = spcls.__name__
        spcls_path = inspect.getfile(spcls)

        global_cfg_files = sconf.get_sources(False)
        sp_cfg_file = sconf.closest_scrapy_cfg(spcls_path)
        cfg_files = [*global_cfg_files, sp_cfg_file]
        cfg = ConfigParser()
        cfg.read(cfg_files)

        # find the relevant entry in the respective config by iterating
        # over entries in config settings section, and find right entry
        # or default
        try:
            cfg_settings_sect = cfg['settings']
        except KeyError:
            logger.debug('Skipping settings import from ancestor "{}". '
                         'Cannot find scrapy.cfg file'.format(spcls_name))
            return

        pkg = spcls.__module__.split('.')[0]
        sttngs_path = cfg_settings_sect.get('default')

        for prj_name, sttngs in cfg_settings_sect.items():
            if prj_name == pkg:
                sttngs_path = sttngs
                break

        rel_sttngs_path = '.{}'.format(sttngs_path.split('.', 1)[1])
        logger.debug('Importing settings file of ancestor "{}" '
                     'from module "{}"'.format(spcls_name, sttngs_path))
        try:
            settings_mdl = importlib.import_module(rel_sttngs_path, pkg)
            return settings_mdl
        except ModuleNotFoundError:
            logger.debug('Skipping settings import from ancestor "{}". '
                         'Cannot find settings.py file'.format(spcls_name))

    @classmethod
    def _get_ancestors(cls):
        '''
        Separate method for returning ancestors to enable
        order overriding. Settings from each ancestor are applied
        first to last.
        '''

        # ignore self, and return in reverse order, so eldest settings
        # are overriden by later ones.
        return [kls for kls in cls.__mro__[1:] if issubclass(kls, scrapy.Spider)][::-1]


class LocalSettingsSpiderMixin(scrapy.Spider):
    '''
    Allow spiders to load settings from a settings.py file found in same
    directory

    Local settings take priority between project settings and
    spider settings (local settings override project and global settings
    and are overriden by spider or cli settings)
    '''

    @classmethod
    def update_settings(cls, settings):
        '''
        Update settings with spider's custom_settings, taking into
        consideration local settings.py file, if one is present.
        '''

        logger = logging.getLogger(getattr(cls, "name") or __name__)

        # Allow other mixins such as AncestorSettingSpiderMixin to apply
        # settings first
        supercls = super().update_settings(settings)

        local_settings = cls._get_local_settings()
        settings.update(vars(local_settings))

        logger.info('Loaded local settings file for "{}"'.format(cls.__name__))

        # Override local settings with spider's custom settings
        scrapy.Spider.update_settings(settings)

    @classmethod
    def _get_local_settings(cls, spcls=None):
        '''
        Search for local settings file for a scrapy.Spider class.

        If class `spcls` is given, searches for its local settings.
        Searches for own local settings file if no class is given.

        Returns settings dictionary on success, or None if the file does not 
        exist or import raised ModuleNotFoundError.
        '''

        kls = cls if spcls is None else spcls
        logger = logging.getLogger(getattr(kls, "name") or __name__)

        spkls_name = kls.__name__
        cls_dir = util.get_dir(kls)
        settings_path = Path(cls_dir, 'settings.py')
        try:
            local_settings = util.local_module(kls, 'settings.py')
            return local_settings
        except ValueError:
            logger.debug('No local settings file found for spider "{}" '
                         'in directory "{}"'.format(spkls_name, cls_dir))
        except ModuleNotFoundError:
            logger.warning('Cannot import local settings file from "{}" '
                           'for spider "{}". Reason: {}'.format(
                               spkls_name, settings_path, tb.format_exc()))


class SeleniumSpiderMixin(scrapy.Spider):
    '''
    This Mixin enables to uses selenium to get website info.

    On some websites, spiders may need to run frontend code to generate 
    initial session ID necessary for valid API requests. In other cases
    website may need to be rendered to obtain relevant data. In those 
    cases, Selenium or Splash are necessary. 

    Mixin uses following variables:

    - `browser` - type of the webdriver. Webdriver and the browser need to be 
                installed on the system. Default: `'chrome'`

    - `browser_options` - list of strings or space-delimeted string options 
                        passed to the webdriver. Default: `'--no-sandbox',
                        '--disable-dev-shm-usage'`

    - `browser_cookies` - Cookies to be uesd with Selenium requests. 
                        Default: `None`

    - `browser_cookies_url` - URL used for getting session cookies. 
                            Default: `None`

    - `browser_loglevel` - Log level of webdriver instance.
    '''

    browser = 'chrome'
    headless = True
    browser_options = None
    browser_cookies = None
    browser_cookies_url = None
    browser_loglevel = logging.INFO

    def __init__(self, browser=None, headless=None, browser_options=None,
                 browser_cookies=None, browser_cookies_url=None,
                 browser_loglevel=None, *args, **kwargs):

        super().__init__(*args, **kwargs)

        self.browser_options = [
            '--no-sandbox',
            '--disable-dev-shm-usage'
        ]

        if browser:
            self.browser = browser
        if headless is not None:
            self.headless = headless
        if browser_options:
            self.browser_options = browser_options
        if isinstance(self.browser_options, str):
            self.browser_options = self.browser_options.split()
        if browser_cookies:
            self.browser_cookies = browser_cookies_url
        if browser_cookies_url:
            self.browser_cookies_url = browser_cookies_url
        if browser_loglevel:
            self.browser_loglevel = browser_loglevel or \
                self.logger.getEffectiveLevel()

        self._setup_webdriver(self.browser, self.browser_options,
                             headless=self.headless, loglevel=self.browser_loglevel)

    def run_webdriver_tasks(
        self,
        webdriver,
        tasks,
        cookies=None,
        start_url=None,
    ):
        '''
        Execute a list of tasks within a single webdriver context.

        Tasks are functions that accept webdriver as the only argument.

        Optionally, specify cookies to be used throughout the selenium session,
        and initial URL to load (Selenium needs to load a page first to be able
        to assign cookies). By default, these are instance properties 
        `browser_cookies` and `browser_cookies_url`.
        '''

        cks = cookies or self.browser_cookies
        url = start_url or self.browser_cookies_url

        with webdriver as wd:
            if url:
                wd.get(url)
            if cks:
                # Cookies can be passed only after webdriver was initialized
                # with a website
                self.logger.debug('Setting cookies for webdriver tasks')
                util.lmap(wd.add_cookie, cks)
            self.logger.debug('Running webdriver tasks')
            results = util.lmap(lambda fn: fn(wd), tasks)
            self.logger.debug('Closing webdriver')
        return results

    def _setup_webdriver(
        self,
        browser=None,
        browser_options=None,
        headless=None,
        loglevel=None
    ):
        '''Set up a webdriver instance'''

        brw_name = browser if browser is not None else self.browser
        brw_options = browser_options if browser_options is not None else self.browser_options
        loglvl = loglevel if loglevel is not None else self.browser_loglevel
        hdls = headless if headless is not None else self.headless

        selenium_logger.setLevel(loglvl)

        brw = self._get_webdriver_class(brw_name)
        opt = self._get_webdriver_options(brw)
        opt.headless = hdls
        util.lmap(opt.add_argument, brw_options)

        self.logger.debug('Initializing webdriver "{}" with options {}.'
                          .format(brw_name, brw_options))
        self.webdriver = brw.webdriver.WebDriver(options=opt)
        return self.webdriver

    def _get_webdriver_options(self, browserclass):
        class NullOptions:
            class Options:
                pass

        opt_cls = getattr(browserclass, 'options', NullOptions)
        opt = opt_cls.Options()
        return opt

    def _get_webdriver_class(self, browser=None):
        brw = browser or self.browser
        return getattr(selenium.webdriver, brw)


# class BrowsermobSeleniumSpiderMixin(SeleniumSpiderMixin):
#     '''
#     This Mixin enables to uses selenium proxied via BrowserMob Proxy.

#     BrowserMob Proxy or BrowserUp Proxy executable is required.

#     On some websites, spiders may need to run frontend code to generate
#     initial session ID necessary for valid API requests. In other cases
#     website may need to be rendered to obtain relevant data. In those
#     cases, Selenium or Splash are necessary.

#     BrowserMobProxy enables network interception or traffic monitoring. For
#     more info, see https://browsermob-proxy-py.readthedocs.io/en/stable/ and
#     https://github.com/browserup/browserup-proxy.

#     Mixin uses following variables:

#     - `browser` - type of the webdriver. Webdriver and the browser need to be
#                 installed on the system. Default: `'chrome'`

#     - `browser_options` - list of strings or space-delimeted string options
#                         passed to the webdriver. Default: `'--no-sandbox',
#                         '--disable-dev-shm-usage'`

#     - `browser_cookies` - Cookies to be uesd with Selenium requests.
#                         Default: `None`

#     - `browser_cookies_url` - URL used for getting session cookies.
#                             Default: `None`

#     - `browser_loglevel` - Log level of webdriver instance.

#     - `bmp_proxy_path` - Path to the BrowserMob Proxy executable.
#     '''

#     bmp_proxy_path = None

#     def __init__(self, proxy_path=None, *args, **kwargs):
#         super().__init__(*args, **kwargs)

#         self.logger.warning('BrowsermobSeleniumSpiderMixin is untested. '
#                             'Things may break.')

#         if proxy_path:
#             self.bmp_proxy_path = proxy_path
#         else:
#             self.bmp_proxy_path = os.environ.get('BROWSERMOB_PROXY_PATH',
#                                                  'browsermob-proxy')

#         self.bmp_server = Server(self.bmp_proxy_path)
#         self.bmp_server.start()
#         self.bmp_proxy = self.bmp_server.create_proxy()

#     @classmethod
#     def from_crawler(cls, crawler, *args, **kwargs):
#         spider = super().from_crawler(crawler, *args, **kwargs)
#         crawler.signals.connect(spider.spider_closed,
#                                 signal=signals.spider_closed)
#         return spider

#     def spider_closed(self, spider):
#         self.bmp_server.stop()
#         self.webdriver.quit()
#         spider.logger.info('Spider closed: %s', spider.name)

#     def _setup_webdriver(
#         self,
#         browser=None,
#         browser_options=None,
#         headless=True,
#         loglevel=None
#     ):
#         '''
#         Sets up a selenium webdriver which uses BrowserMob Proxy
#         as a proxy
#         '''

#         if browser.lower() not in ['firefox', 'chrome']:
#             return super()._setup_webdriver(browser, browser_options,
#                                             headless, loglevel)

#         brw_name = browser or self.browser
#         brw_options = browser_options or self.browser_options
#         loglvl = loglevel or self.browser_loglevel

#         selenium_logger.setLevel(loglevel)

#         brw = self._get_webdriver_class(brw_name)
#         opt = self._get_webdriver_options(brw)
#         opt.headless = headless
#         util.lmap(opt.add_argument, brw_options)

#         if brw_name.lower() == 'firefox':
#             profile = webdriver.FirefoxProfile()
#             profile.set_proxy(self.bmp_proxy.selenium_proxy())
#             self.webdriver = brw.webdriver.WebDriver(
#                 firefox_profile=profile, options=opt)
#         elif brw_name.lower() == 'chrome':
#             opt.add_argument("--proxy-server={0}".format(self.bmp_proxy.proxy))
#             self.webdriver = brw.webdriver.WebDriver(chrome_options=opt)

#         return self.webdriver


class SubclassMixin():
    '''Pass the context from the outer scope into the class'''

    def __init__(self, context=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.context = context
