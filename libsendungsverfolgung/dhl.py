import requests

from . import base

class DHL(object):

    SLUG = "dhl"
    SHORTNAME = "DHL"
    NAME = "Deutsche Post DHL"

    @classmethod
    def get_parcel(cls, tracking_number):

