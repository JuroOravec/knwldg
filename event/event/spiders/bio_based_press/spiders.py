from event.spiders.events_calendar import EventsCalendarSpider


class BioBasedPressEventSpider(EventsCalendarSpider):

    name = 'bio_based_press_event'
    base_url = 'https://www.biobasedpress.eu'
    events_path = '/events/'
    source = 'Bio Based Press'
    custom_settings = {
        'ITEM_PIPELINES': {
            'event.spiders.bio_based_press.pipelines.BioBasedPressEventPipeline': 400,
            'event.pipelines.EventTypePipeline': 401,
            'event.pipelines.EventLocationPipeline': 402,
            'event.pipelines.EventDatePipeline': 403,
            'event.pipelines.UrlCleanerPipeline': 404,
            'event.pipelines.EventMetadataPipeline': 405,
            'event.pipelines.StripperPipeline': 406,
            'common.pipelines.CsvWriterPipeline': 900,
        }
    }
