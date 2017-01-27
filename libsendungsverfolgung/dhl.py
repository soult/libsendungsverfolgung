import datetime
import html.parser
import itertools
import operator
import re
import requests
import time

from . import base
from .events import *

class Location(base.Location):
    pass

class Store(base.Store):
    pass

class Parcel(base.Parcel):

    COMPANY_IDENTIFIER = "dhl"
    COMPANY_NAME = "Deutsche Post DHL"
    COMPANY_SHORTNAME = "DHL"

    class EventsParser(html.parser.HTMLParser):

        STATE_TABLE = 2**0
        STATE_TBODY = 2**1
        STATE_ROW = 2**2
        STATE_DATE = 2**3
        STATE_LOCATION = 2**4
        STATE_STATUS = 2**5

        def __init__(self, *args, **kwargs):
            super(Parcel.EventsParser, self).__init__(*args, **kwargs)

            self.events = []
            self._state = self.STATE_TABLE

        def handle_starttag(self, tag, attrs):
            if tag == "tbody" and self._state == self.STATE_TABLE:
                self._state = self.STATE_TBODY
            elif tag == "tr" and self._state == self.STATE_TBODY:
                self._state = self.STATE_ROW
                self._time = ""
                self._status = ""
                self._location = ""
            elif tag == "td" and self._state == self.STATE_ROW:
                label = None
                for k, v in attrs:
                    if k == "data-label":
                        label = v
                        break

                if label == "Datum/Uhrzeit":
                    self._state = self.STATE_DATE
                elif label == "Ort":
                    self._state = self.STATE_LOCATION
                elif label == "Status":
                    self._state = self.STATE_STATUS

        def handle_endtag(self, tag):
            if tag == "tbody":
                assert self._state == self.STATE_TBODY
                self._state = self.STATE_TABLE
            elif tag == "tr" and self._state == self.STATE_ROW:
                self._state = self.STATE_TBODY
                self._add_event(self._time.strip(), self._status.strip(), self._location.strip())
            elif tag == "td" and self._state in (self.STATE_DATE, self.STATE_LOCATION, self.STATE_STATUS):
                self._state = self.STATE_ROW

        def handle_data(self, data):
            if self._state == self.STATE_DATE:
                self._time += data
            elif self._state == self.STATE_LOCATION:
                self._location += data
            elif self._state == self.STATE_STATUS:
                self._status += data

        def _add_event(self, time, status, location):
            when = datetime.datetime.strptime(time[5:], "%d.%m.%Y %H:%M h")
            if location == "--":
                location = None
            else:
                location = Location(city=location)

            if status == "The instruction data for this shipment have been provided by the sender to DHL electronically":
                self.events.append(DataReceivedEvent(when))
            elif status == "The shipment has been posted by the sender at the retail outlet":
                self.events.append(PostedEvent(location, when))
            elif status == "The shipment has been picked up":
                self.events.append(PickupEvent(location, when))
            elif status == "The shipment has been processed in the parcel center of origin":
                self.events.append(SortEvent(location, when))
            elif status == "The shipment has been processed in the destination parcel center":
                self.events.append(SortEvent(location, when))
            elif status == "The item has been sent.":
                self.events.append(DeliveryDropOffEvent(None, when))
            else:
                self.events.append(ParcelEvent(when))


    def __init__(self, tracking_number, *args, **kwargs):
        self._tracking_number = str(tracking_number).upper()
        self._data = None

    @classmethod
    def from_barcode(cls, barcode):
        if re.match(r"^\d{12}$", barcode):
            check_digit = 10 - (sum(itertools.starmap(operator.mul, zip(itertools.cycle((4, 9)), map(int, barcode[:-1])))) % 10)
            if check_digit == 10:
                check_digit = 0
            if check_digit == int(barcode[-1]):
                return cls(barcode)

        if re.match(r"^\d{20}$", barcode):
            check_digit = 10 - (sum(itertools.starmap(operator.mul, zip(itertools.cycle((3, 1)), map(int, barcode[:-1])))) % 10)
            if check_digit == 10:
                check_digit = 0
            if check_digit == int(barcode[-1]):
                return cls(barcode)

        match = re.match(r"^JJD(\d{13,24})$", barcode, re.IGNORECASE)
        if match:
            match_length = len(match.group(1))
            if match_length in (13, 16, 17, 18, 20, 24):
                return cls(barcode)

    def fetch_data(self):
        if self._data:
            return

        params = {
            "lang": "en",
            "idc": self.tracking_number
        }
        r = requests.get("https://nolp.dhl.de/nextt-online-public/set_identcodes.do", params=params)

        self._data = r.text

    @property
    def tracking_number(self):
        return self._tracking_number

    @property
    def events(self):
        self.fetch_data()
        match = re.search(r"<table class=\"mm_event_table\">(.*?)</table>", self._data, re.MULTILINE + re.DOTALL)
        if not match:
            raise Exception("Unable to locate event table")
        event_table = match.group(1)

        parser = self.EventsParser()
        parser.feed(event_table)

        return parser.events
