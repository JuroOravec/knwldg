
# Flow of scraping site: www.infogreffe.fr
#
# 1) BaseSpider
#
#    -  Common behavior
#
# 2) SearchGeneratorSpider
#
#    -  Generate search requests based on name and sector ID at url:
#       https://www.infogreffe.fr/services/entreprise/rest/recherche/parEntreprise
#
#
# 3) SearchParserSpider
#
#    -  Parse search results and extract company IDs. Generate new
#       requests fetching details based on those IDs and POST them to url:
#       https://www.infogreffe.fr/services/entreprise/rest/recherche/resumeEntreprise?typeRecherche=ENTREP_RCS_ACTIF
#       If the search yielded more results than can be shown, generate new
#       requests for the same search, but with more specific name parameter.
#
#       Notes:
#         - At the time of writing, the limit is 99 entries shown per search
#
# 4) DetailsSpider
#
#    -  Parse company details.
#
#
# All of the above is composed into InfogreffeSpider.
#
#
#
# Data structure:
# {
#   "success":true,
#   "identifier":"id",
#   "label":"deno",
#   "loadedAttr":"numeroDossier",
#   "idRecherche":null,
#   "nbTotalResultats":0,
#   "items":[
#       {
#           "id":14571573,
#           "numeroDossier":"180116B00305", --> internal ID;  part of url
#           "etablissementChrono":"0000", --> ID in case of changes? also part of url
#           "libelleEntreprise":{
#               "denomination":"C ET CIE", --> Trading name
#               "denominationEirl":null,
#               "enseigne":"C ET CIE",  --> brand name
#               "nomCommercial":null, --> Trading name?
#               "sigle":null --> acronym
#           },
#           "siret":821404746, --> FR company ID and part of url
#           "nic":"00017",
#           "adresse":{ ---> address
#               "lignes":[
#                   "ROUTE D'ACHÈRES",
#                  "POLE ISAAC NEWTON"
#               ],
#               "codePostal":"18250",
#               "bureauDistributeur":"HENRICHEMONT"
#           },
#           "codePaysRegistreEtranger":null,
#           "greffe":{
#               "numero":"1801",
#               "nom":"BOURGES",
#               "codeGroupement":"05",
#               "codeEDI":"G1801",
#               "typeTribunalReel":"TC",
#               "nomGreffeMin":null
#           },
#           "typeEtab":"SIE",
#           "produitAuPanier":"AJOUTABLE",
#           "typeInscription":1,
#           "sourceDonnees":"GTC",
#           "radie":false,
#           "dateRadiation":null,
#           "nbEtablissements":1,
#           "activite":{
#               "codeNAF":"2042Z",
#               "libelleNAF":"Fabrication de parfums et de produits pour la toilette"
#           },
#           "etatSurveillance":"SURVEILLABLE"
#       }
#   ],
#   "typeProduitMisEnAvant":"EXTRAIT",
#   "critereRecherchePrincipal":null,
#   "entrepRechInfosComplementaires":null
# }


import copy
import json
import re
import requests
from urllib import parse, request
import uuid

import scrapy

from fr import exceptions
import common.util as util
import common.components as components


class BaseSpider(scrapy.Spider, components.TimeTaggedMixin):
    '''Base class with common behavior for www.infogreffe.fr spiders'''

    default_cookies = None

    def __init__(self, default_cookies=None, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.default_cookies = [{
            'name': 'GUEST_LANGUAGE_ID',
            'value': 'en_US'
        }]

        if default_cookies:
            if getattr(default_cookies, "items", None):
                self.default_cookies = [default_cookies]
            else:
                self.default_cookies = default_cookies


class SearchGeneratorSpider(BaseSpider,
                            components.StringCombinationsMixin,
                            components.ComposableSpiderMixin,):
    '''
    Spider generating search requests by name and sector.

    This spider is a separate class to decouple initial request generation
    and downstream request processing.
    '''

    name = "fr_infogreffe_search_generator"

    def start_requests(self):
        # Go over each sector, and try out all string combinations as name.
        # Faster than going over IDs alone and generates more specific
        # requests than going over name alone, so fewer repeated search
        # requests.
        for sector_id in self._get_sector_ids():
            names = self.string_combinations.generate(seed="")
            for name in names:
                yield self.build_request_from_params(name=name,
                                                     sector_id=sector_id,
                                                     callback=self.parse)

    @classmethod
    def build_request_from_params(cls, name=None, siret_id=None, sector_id=None,
                                  location=None, include_dissoved=False,
                                  include_branches=False, **kwargs):
        '''
        Construct search request based on name, siret ID, 
        sector ID, or location.
        '''

        url_template = "https://www.infogreffe.fr/services/entreprise/rest/recherche/parEntreprise?params&{}"

        if not name and not siret_id:
            raise ValueError('At least one of {} needs to be specified to '
                             'generate a search request'.format(
                                 ['name', 'siret_id']))
        param_true = "true"
        param_false = "false"

        params = {
            "typeProduitMisEnAvant": "EXTRAIT",
            "domaine": "FR",
            "typeEntreprise": "TOUS",
            "surveillanceVisible": param_true,
            "miseAupanierVisible": param_true,
            "etsRadiees": param_true if include_dissoved else param_false,
            "etabSecondaire": param_true if include_branches else param_false
        }

        queried = {}

        if name:
            params["deno"] = name
            queried['name'] = name
        if siret_id:
            params["siretOuSiret"] = siret_id
            queried['id'] = siret_id
        if sector_id:
            sector = str(sector_id).zfill(2) if sector_id else ''
            params["familleActivite"] = sector
            queried['sector'] = sector
        if location:
            params["localisation"] = location
            queried['location'] = location

        qs = parse.urlencode(params)
        url = url_template.format(qs)

        meta = {
            "query": queried
        }

        req = cls.build_request(url, meta=meta, **kwargs)
        return req

    @classmethod
    def build_request(cls, url, **kwargs):
        '''Create request with default options relevant at this stage.'''

        def raise_search_req_exc(res):
            raise exceptions.SearchRequestException(r)

        req_kwargs = {
            "cookies": cls.default_cookies,
            "dont_filter": True,
        }
        req_kwargs.update(kwargs)
        req = scrapy.http.Request(url, **req_kwargs)
        if "cookiejar" not in req.meta:
            req.meta['cookiejar'] = str(uuid.uuid4())
        return req

    def _get_sector_ids(self):
        # Sector IDs are from 1-99
        return range(1, 100)


class SearchParserSpider(BaseSpider,
                         components.LimitedResultsByQueryNameResolverMixin,
                         components.ComposableSpiderMixin,):
    '''
    Extracts IDs search results from the Infogreffe.fr business registry
    Data taken from https://www.infogreffe.com/,
    '''

    name = "fr_infogreffe_search_parser"
    query_param = 'deno'
    max_batch_size = 500

    def __init__(self, max_batch_size=None, *args, **kwargs
                 ):
        super().__init__(*args, **kwargs)

        if max_batch_size:
            self.max_batch_size = max_batch_size

    def parse(self, response, **kwargs):
        '''
        Parse company IDs from the response.

        If the number of responses reached the limit, make new requests
        with longer name query and resubmit the requests to the spider's queue.
        '''

        self.logger.debug("Parsing response {}".format(response))

        json_res = json.loads(response.text)

        # Response consists of results from multiple data stores. If for any
        # of the stores, the results have hit the limit on the number of entries,
        # repeat the search with more specific query.
        results_limited = self.map_results([self.is_result_limited], json_res)
        results_limited = any(results_limited[0].values())
        if results_limited:
            totals, limits = self.map_results(
                [self.results_total, self.results_limit],
                json_res)
            total = sum(totals.values())
            limit = max(limits.values())
            self.logger.info(
                'Search "{}" in sector {} is too broad. '
                'Resubmitting the search with longer query. '
                'Results: {} Limit: {}. '.format(
                    response.meta['query']['name'], response.meta['query']['sector'],
                    total, limit)
            )
            return self.build_search_requests(response)

        # None of the results have hit the limit, so we've got everything
        # there is and we can process the response.
        company_id_groups = self.map_results(
            [self.parse_results], json_res)[0]

        company_ids = [id
                       for id_group in company_id_groups.values()
                       for id in id_group]

        self.logger.info(
            'Found {} entities for search "{}" in sector {}'.format(
                len(company_ids), response.meta['query']["name"],
                response.meta['query']['sector']
            )
        )

        reqs = self.build_detail_requests(company_ids,
                                          request=response.request,
                                          headers=response.headers,
                                          **kwargs)

        return self.resolve_output(reqs)

    def map_results(self, tasks, response, include_registered=True,
                    include_nonregistered=True, include_other=True):
        '''
        Runs tasks against individual groups of results (stores) in a response
        from www.infogreffe.fr/services/entreprise/rest/recherche/parEntreprise

        Returns lists of results of these tasks.

        Result lists have following order:
        - Registered entities
        - Not-registered entities
        - Other

        Excluding any of the groups will result in shortened results list.
        '''

        stores_names = {
            'entrepRCSStoreResponse': 'registered',
            'entrepHorsRCSStoreResponse': 'nonregistered',
            'entrepMultiStoreResponse': 'other'
        }
        stores_options = {
            'entrepRCSStoreResponse': include_registered,
            'entrepHorsRCSStoreResponse': include_nonregistered,
            'entrepMultiStoreResponse': include_other
        }
        res_stores = {}
        for k, v in stores_options.items():
            if v:
                res_stores[stores_names[k]] = response.get(k)

        results = [util.map_dict_val(task, res_stores) for task in tasks]
        return results

    def build_search_requests(self, response):
        # New urls resolved by LimitedResultsByQueryResolverMixin
        new_urls = self.resolve_result_limit(response)
        for new_url, _, qobj in new_urls:
            # New requests should not inherit any cookies nor headers
            # from the response as this may invalidate the requests.
            meta = {
                "query": response.meta.get('query', {})
            }
            meta['query']['name'] = qobj[self.query_param]
            req = SearchGeneratorSpider.build_request(new_url, meta=meta)
            yield req

    def build_detail_requests(self, company_ids, request=None, **kwargs):
        def raise_details_req_exc(res):
            raise exceptions.DetailRequestException(response)

        url = "https://www.infogreffe.fr/services/entreprise/rest/recherche/resumeEntreprise/?typeRecherche=ENTREP_RCS_ACTIF"

        make_req = request.replace if request else scrapy.Request
        req_kwargs = {
            'url': url,
            'method': "POST",
            'dont_filter': True,
        }
        req_kwargs.update(**kwargs)
        new_req = make_req(**req_kwargs)
        if 'cookies' not in kwargs:
            util.update_request_cookies(
                new_req, pattern=r'WSCACHEID|BIGipServer')
        # Details request specifically requires following Content-Type
        new_req.headers['Content-Type'] = 'text/plain'

        for ids in util.grouper(self.max_batch_size, company_ids):
            ids = util.lfilter(None, ids)
            body = ",".join(util.map2str(ids)).replace(' ', '')
            req = new_req.replace(body=body)
            yield req

    def parse_results(self, result):
        '''Parse company IDs from single result group within a response.'''

        if not result:
            return []
        if not result.get('success'):
            raise exceptions.SearchRequestException(result)
        items = util.lfilter(None, map(
            lambda d: d.get('id'),
            result.get('items') or []
        ))
        return items

    def is_result_limited(self, result):
        result_count = result.get('nbTotalResultats') or 0
        items_count = len(result.get('items') or [])
        if items_count < result_count:
            self.logger.debug('Search found more results than can be '
                              'displayed ({} of {})'
                              .format(items_count, result_count))
            return items_count < result_count

    def results_total(self, result):
        return result.get('nbTotalResultats') or 0

    def results_limit(self, result):
        return len(result.get('items') or [])


class DetailsSpider(BaseSpider,
                    components.ComposableSpiderMixin,):

    """
    Parses entry details from Infogreffe.fr business registry's API
    Data taken from https://www.infogreffe.com/,
    """

    name = "fr_infogreffe_details_parser"

    country = "France"
    economic_area = "EEA"

    def __init__(self, country=None, economic_area=None, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if country:
            self.country = country
        if economic_area:
            self.economic_area = economic_area

        self.sector_desc = self.get_sector_desc()

    def get_sector_desc(self):
        '''Scrape sectorID-to-description mapping'''

        sector_url = 'https://www.infogreffe.com/services/commun/rest/referentiel/FAMILLE_ACTIVITE/en'

        self.logger.debug('Fetching sector descriptions from {}'.format(
            sector_url))
        res = requests.get(sector_url)
        payload = res.json()

        if not payload.get('success'):
            if not payload.get('message'):
                self.logger.warning('Unknown error fetching sector '
                                    'descriptions.')
            else:
                self.logger.warning('Error fetching sector descriptions: {}'
                                    .format(payload['message']))
            return []
        id = payload.get('identifier')
        attr = payload.get('label')
        desc = {
            item[id]: item[attr].split('-', 1)[1]
            for item in payload.get('items', [])
        }
        return desc

    def parse(self, response):
        '''Parse details'''

        self.logger.debug("Processing response {}".format(response))

        res_body = json.loads(response.body.decode('utf-8'))
        if not res_body.get('success'):
            raise exceptions.DetailRequestException(response)

        items = res_body.get('items') or []
        items = [self.parse_item(itm, response) for itm in items]
        items = map(util.flatten_json, items)

        return self.resolve_output(items)

    def parse_item(self, item, response):
        '''Parse single details item'''

        queried = response.meta.get('query')
        sector_id = queried.get('sector', '-1')

        itm = copy.deepcopy(item)
        url_id = self.build_url_id(itm)
        itm['url_id'] = url_id
        itm['sector_id'] = sector_id
        itm['sector_desc'] = self.sector_desc.get(sector_id, '')
        itm['registry'] = self.build_registry_url(url_id)
        itm['country'] = self.country
        itm['economic_area'] = self.economic_area
        for k in queried:
            itm[f'meta_query_{k}'] = queried.get(k, '')
        return itm

    def build_registry_url(self, url_id):
        url_template = "https://www.infogreffe.fr/entreprise-societe/{}.html"
        return url_template.format(url_id)

    def build_url_id(self, data):
        '''
        The URL of a company's webpage is specified by an ID which consists
        of an escaped name of the company, it's ID, and two other identifier.
        '''

        try:
            id = data['id']
            name = data['libelleEntreprise']['denomination'].lower()
            name = re.sub('\W', ' ', name).replace(' ', '-')
            id1 = data['numeroDossier']
            id2 = data['etablissementChrono']
            url_id = '{}-{}-{}{}'.format(id, name, id1, id2)
            return url_id
        except KeyError:
            self.logger.error('Failed to build URL ID: \n{}'.format(
                traceback.format_exc()
            ))
            return ''


class InfogreffeSpider(components.ComposableSpiderMixin,):
    '''
    Composite class combining the whole workflow of scraping infogreffe.fr
    into a single spider.
    '''

    name = "fr_infogreffe_spider"

    class SearchGeneratorSpider(SearchGeneratorSpider,
                                components.SubclassMixin,):

        def resolve_output(self, results):
            for res in results:
                new_reqs = self.context._search_parse_spider.parse(
                    res, callback=self.context.parse)
                return new_reqs

    SearchParserSpider = SearchParserSpider
    DetailsSpider = DetailsSpider

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._search_gen_spider = self.SearchGeneratorSpider(
            context=self, *args, **kwargs)
        self._search_parse_spider = self.SearchParserSpider(
            context=self, query_param="deno", *args, **kwargs)
        self._detail_parse_spider = self.DetailsSpider(*args, **kwargs)

    def start_requests(self):
        reqs = self._search_gen_spider.start_requests()
        for req in reqs:
            yield req

    def parse(self, response):
        api = 'infogreffe.(?:fr|com)/services/entreprise/rest'
        search_endpoint = '/recherche/parEntreprise'
        detail_endpoint = '/recherche/resumeEntreprise/'
        search_pattern = re.compile(api + search_endpoint)
        detail_pattern = re.compile(api + detail_endpoint)

        url = response.url
        if search_pattern.search(url):
            return self._search_parse_spider.parse(response)
        elif detail_pattern.search(url):
            return self._detail_parse_spider.parse(response)
        return self.resolve_output([response])


class InfogreffeNoGenSpider(components.ComposableSpiderMixin,):
    '''
    Composite class combining the workflow of scraping infogreffe.fr
    into a single spider, except of generating the initial search url.
    '''

    name = "fr_infogreffe_no_gen_spider"

    class SearchParserSpider(SearchParserSpider,
                             components.SubclassMixin,):

        def resolve_output(self, reqs):
            reqs = list(reqs)
            for req in reqs:
                req.callback = self.context.parse
            return reqs

    DetailsSpider = DetailsSpider

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._search_parse_spider = self.SearchParserSpider(
            context=self, *args, **kwargs)
        self._detail_parse_spider = self.DetailsSpider(
            context=self, *args, **kwargs)

    def parse(self, response):
        api = 'infogreffe.(?:fr|com)/services/entreprise/rest'
        search_endpoint = '/recherche/parEntreprise'
        detail_endpoint = '/recherche/resumeEntreprise/'
        search_pattern = re.compile(api + search_endpoint)
        detail_pattern = re.compile(api + detail_endpoint)

        url = response.url
        if search_pattern.search(url):
            return self._search_parse_spider.parse(response)
        elif detail_pattern.search(url):
            return self._detail_parse_spider.parse(response)
        return self.resolve_output([response])
