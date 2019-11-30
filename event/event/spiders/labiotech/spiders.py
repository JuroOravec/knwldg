from event.spiders.events_calendar import EventsCalendarSpider


class LabiotechEventSpider(EventsCalendarSpider):

    name = 'labiotech_event'
    base_url = 'https://www.labiotech.eu'
    events_path = '/events/list/'
    source = 'Labiotech'
    custom_settings = {
        'ITEM_PIPELINES': {
            'event.spiders.labiotech.pipelines.LabiotechEventPipeline': 400,
            'event.pipelines.EventTypePipeline': 401,
            'event.pipelines.EventLocationPipeline': 402,
            'event.pipelines.EventDatePipeline': 403,
            'event.pipelines.UrlCleanerPipeline': 404,
            'event.pipelines.EventMetadataPipeline': 405,
            'event.pipelines.StripperPipeline': 406,
            'common.pipelines.CsvWriterPipeline': 900,
        }
    }
