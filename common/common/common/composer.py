from abc import abstractmethod
from collections import deque
from functools import reduce
import numbers
from operator import itemgetter

from inline_requests import inline_requests
import scrapy
from scrapy.http import Response
from scrapy.settings import BaseSettings
from scrapy.utils.misc import load_object, create_instance
from scrapy.utils.conf import build_component_list
from scrapy.utils.deprecate import update_classpath
from scrapy.utils.python import without_none_values
import six

from common.util import conditional_deco, dol2lot, lfilter


class Composer(scrapy.Spider):
    '''
    Compose multiple spider classes into one.

    URLs to crawl are taken from the first spider. Then, for each spider
    including the first one, the response is passed to the spider's parse
    function (as specified by the `callback` attribute of the request, or
    defaulted to `spider.parse`), and the parsed result (a new scrapy.Request)
    is passed to the subsequent spider, who fetches the Response and passes
    it to its parse function, and so on.

    Parse functions of all spiders, except the last, must return either
    a Request or an iterable of Requests. If a spider returns an iterable,
    each of the Requests will be passed through all of the downstream spiders.

    Composed spiders are defined by defining spider's `spiders` attribute.
    `spiders` expects a dictionary similar to other scrapy components in the
    form of `'spider.class.path': priority|[priority]`.

    A single spider class can be used in a composite spider at multiple places,
    by providing a list of priorities, instead of a single value.

    To use a single instance of a spider at these multiple priorities, set
    `initialize_once` to `True`

    Requests from each spider can be either be fetched within the same instance,
    or the request can be yielded back to scrapy by setting `yield_requests` to
    `True`. This can be desirable if the logic  for chosing the instance of the
    next spider is more complex, such as when using scrapy-cluster.

    To support callbacks when possibly passing the requests to different
    spider instances, the callback can be defined also as a string defining:

    a) attribute path to the method within the instance that does the parsing

    So `handlers.handle_response` would call self.handlers.handle_response

    b) a composition of an import path to the object which is or holds the
    callback method, and (optionally) of attribute path to the method within
    the object, delimeted by space ` `.

    `{importpath}{delim}{methodpath}`

    So `scrapy.http.Response css` would call method `css` of class Response
    imported from `scrapy.http`


    Example usage:

    The following composite class will run spiders in the following order:

    SpiderOne -> SpiderTwo -> SpiderOne -> SpiderThree

    >>> class CompositeSpider(Composer):
    >>>     spiders = {
    >>>         'common.spiders.SpiderOne': [1, 3],
    >>>         'common.spiders.SpiderTwo': 2,
    >>>         'common.spiders.SpiderThree': 4
    >>>     }

    '''

    yield_requests = True
    initialize_once = True

    @property
    @abstractmethod
    def spiders(self):
        ...

    def __init__(self, crawler, *args,  **kwargs):
        super().__init__(**kwargs)

        splist = self._build_component_list(self.spiders)
        spcache = {}
        spiders = []

        for clspath in splist:
            if self.initialize_once and clspath in spcache:
                spiders.append(spcache[clspath])
                continue
            spcls = load_object(clspath)
            subsp = create_instance(spcls, crawler.settings, crawler,
                                    *args, **kwargs)
            spcache[clspath] = subsp
            spiders.append(subsp)

        if not spiders:
            self.logger.error('Spider Composer cannot be initialized with no'
                              'active spiders')
        self._spiders = spiders

    @classmethod
    def from_crawler(cls, crawler, *args, **kwargs):
        spider = cls(crawler, *args, **kwargs)
        spider._set_crawler(crawler)
        return spider

    def start_requests(self):
        reqs = self._spiders[0].start_requests()
        for req in reqs:
            self._update_callback(req)
            req.meta['composer']['next_spider']: 0
            yield req

    @conditional_deco(inline_requests, lambda slf, *a: not slf.yield_requests)
    def parse(self, response):
        queue = deque([response])
        while queue:
            res = queue.pop()
            compmeta = self._get_composer_meta(res)
            index = compmeta.get('next_spider', 0)
            selfscope = {k: getattr(self, k) for k in dir(self)}
            callback = self._get_callback(compmeta, scope=selfscope)

            spider = self._spiders[index]
            parse_fn = callback if callback is not None else spider.parse
            parsed = parse_fn(res)

            if self._is_last(index):
                # We've run out of spiders, so even if the parsed item was
                # a Request, we will leave it up to the user to submit it
                print("composed spider done!")
                yield parsed
                return
            try:
                reqs = iter(parsed)
            except TypeError:
                reqs = [parsed]

            for req in reqs:
                if not isinstance(req, scrapy.Request):
                    raise TypeError('Intermediate spiders must produce Request'
                                    ' objects or generators thereof. Spider {}'
                                    ' returned {}\n{}'.format(
                                        self._spiders[index].name,
                                        req.__class__.__name__,
                                        req))
                self._update_callback(req)
                self._update_index(req, index=index)
                if self.yield_requests:
                    yield req
                else:
                    new_res = yield req
                    if new_res is not None:
                        queue.append(new_res)
        return

    def _update_callback(self, request, callback=None):
        comp = self._get_composer_meta(request)
        comp['callback'] = request.callback
        request.callback = callback
        return request

    def _update_index(self, req_or_res, index=None):
        comp = self._get_composer_meta(req_or_res)
        comp['next_spider'] = (index or 0) + 1
        return req_or_res

    def _get_composer_meta(self, req_or_res):
        if 'composer' not in req_or_res.meta:
            req_or_res.meta['composer'] = {}
        return req_or_res.meta['composer']

    def _get_callback(self, compmeta, scope=None, delim=' '):
        '''
        Resolve callback. Callback is retrieved from obj.meta['composer']['callback']

        If this path leads to a string and scope is supplied, the string is
        treated as a name of a variable accesible in the scope.

        If scope is not provided, string is treated as composed of import path
        to the object which is or holds the callback method, and of attribute
        path to the method within the object, delimeted by `delim`.

        `{importpath}{delim}{methodpath}`

        Or for example:

        `scrapy.http.Response css`

        Would return the `css` method of `Response` class in `scrapy.http`
        '''

        cbk_or_path = compmeta.get('callback')

        if not isinstance(cbk_or_path, str):
            return cbk_or_path

        # Try whether the string points to a variable (and optionally its
        # attribute) within the scope
        if scope is not None:
            scope_path = lfilter(None, cbk_or_path.split('.'))
            varname = scope_path.pop(0)
            try:
                var = scope[varname]
                return reduce(getattr, scope_path, var)
            except (KeyError, AttributeError):
                pass

        # Handle string as a combination of import path and attribute path
        # delimeted by `delim`
        paths = lfilter(None, cbk_or_path.split(delim))
        if len(paths) == 1:
            paths.append('')
        objpath, methodpath = paths
        obj = load_object(objpath)
        if not methodpath:
            return obj
        callback = reduce(getattr, methodpath.split('.'), obj)
        return callback

    def _is_last(self, i):
        return i + 1 == len(self._spiders)

    def _build_component_list(self, compdict, custom=None, convert=update_classpath):
        """
        Compose a component list from a { class: order|[orders] } dictionary.

        Adapted from scrapy.utils.conf.build_component_list
        """

        def _check_components(complist):
            if len({convert(c) for c in complist}) != len(complist):
                raise ValueError('Some paths in {!r} convert to the same object, '
                                 'please update your settings'.format(complist))

        def _map_keys(compdict):
            if isinstance(compdict, BaseSettings):
                compbs = BaseSettings()
                for k, v in six.iteritems(compdict):
                    prio = compdict.getpriority(k)
                    if compbs.getpriority(convert(k)) == prio:
                        raise ValueError('Some paths in {!r} convert to the same '
                                         'object, please update your settings'
                                         ''.format(list(compdict.keys())))
                    else:
                        compbs.set(convert(k), v, priority=prio)
                return compbs
            else:
                _check_components(compdict)
                return {convert(k): v for k, v in six.iteritems(compdict)}

        def _validate_values(compdict):
            """Fail if a value in the components dict is not a real number or a list of them or None."""
            for name, value in six.iteritems(compdict):
                try:
                    vals = iter(value)
                except:
                    vals = [value]
                for val in vals:
                    if val is not None and not isinstance(val, numbers.Real):
                        raise ValueError('Invalid value {} for component {}, please provide '
                                         'a real number or None instead'.format(val, name))

        # BEGIN Backward compatibility for old (base, custom) call signature
        if isinstance(custom, (list, tuple)):
            _check_components(custom)
            return type(custom)(convert(c) for c in custom)

        if custom is not None:
            compdict.update(custom)
        # END Backward compatibility

        _validate_values(compdict)
        compdict = without_none_values(_map_keys(compdict))
        comptuples = dol2lot(compdict)
        return [k for k, v in sorted(comptuples, key=itemgetter(1))]

