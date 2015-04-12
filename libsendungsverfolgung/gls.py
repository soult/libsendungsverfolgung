import datetime
import decimal
import itertools
import operator
import re
import requests
import time

from . import base
from .events import *

class Location(base.Location):

    def __init__(self, data):
        return super(Location, self).__init__(city=data["city"], country_code=data["countryCode"])

class Store(base.Store):

    DAYS_OF_WEEK = ("Mo", "Tu", "We", "Th", "Fr", "Sa", "Su")

    NOKIA_APP_ID = "s0Ej52VXrLa6AUJEenti"

    @classmethod
    def _parse_opening_hours(cls, data):
        result = []
        current_day = []

        for part in data.split("|"):
            match = re.match("^([A-Z][a-z])\.(?: - ([A-Z][a-z])\.)?: ", part)
            if match:
                if current_day:
                    result[-1] += ",".join(current_day)
                    current_day = []

                day_start = cls.DAYS_OF_WEEK.index(match.group(1))
                if match.group(2):
                    day_end = cls.DAYS_OF_WEEK.index(match.group(2))
                    result.append("%s-%s " % (cls.DAYS_OF_WEEK[day_start], cls.DAYS_OF_WEEK[day_end]))
                else:
                    result.append("%s " % cls.DAYS_OF_WEEK[day_start])
                part = part[len(match.group(0)):]

            match = re.match("^#(\d\d:\d\d) - (\d\d:\d\d)$", part)
            if not match:
                raise ValueError("Unable to parse opening hours")
            current_day.append("%s-%s" % match.groups())

        if current_day:
            result[-1] += ",".join(current_day)

        return "; ".join(result)

    @classmethod
    def from_id(cls, store_id):
        params = {
            "appId": cls.NOKIA_APP_ID,
            "layerId": "48",
            "query": "[like]/name3/%s" % store_id,
            "rangeQuery": "",
            "limit": "1",
        }
        r = requests.get(
            "https://api.customlocation.nokia.com/v1/search/attribute",
            params=params)
        data = r.json()
        if len(data.get("locations", [])) != 1:
            raise ValueError("Invalid store ID")
        data = data["locations"][0]

        opening_hours = cls._parse_opening_hours(data["description"])

        return cls(
            name=data["name1"],
            address=data["street"],
            postcode=data["postalCode"],
            city=data["city"],
            country_code=data["country"],
            phone=data.get("phone"),
            fax=data.get("fax"),
            email=data.get("email"),
            opening_hours=opening_hours
        )

class Parcel(base.Parcel):

    def __init__(self, tracking_number, *args, **kwargs):
        tracking_number = str(tracking_number)
        match = re.match("^([0-9]{11})([0-9])$", tracking_number)
        if match:
            if self.check_digit(match.group(0)) != match.group(1):
                raise ValueError("Invalid check digit")
        elif not (re.match("^[0-9]{11}$", tracking_number) or re.match("^[A-Z0-9]{8}$", tracking_number)):
            raise ValueError("Invalid tracking number")

        super(Parcel, self).__init__(*args, **kwargs)
        self._get_data(tracking_number)

    def _get_data(self, tracking_number):
        params = {
            "caller": "witt002",
            "match": tracking_number,
            "milis": int(time.time() * 1000)
        }
        r = requests.get(
            "https://gls-group.eu/app/service/open/rest/EU/en/rstt001",
            params=params)

        if r.status_code == 404:
            raise ValueError("Unknown tracking number")

        self._data = r.json()
        if not "tuStatus" in self._data:
            raise ValueError("Unknown tracking number")

    def _get_info(self, key):
        for info in self._data["tuStatus"][0]["infos"]:
            if info["type"] == key:
                return info["value"]
    @property
    def weight(self):
        weight = self._get_info("WEIGHT")
        if weight:
            assert weight[-3:] == " kg"
            return decimal.Decimal(weight[:-3])

    @property
    def tracking_number(self):
        tn = self._data["tuStatus"][0]["tuNo"]
        return tn + str(self.check_digit(tn))

    @property
    def product(self):
        return self._get_info("PRODUCT")

    @property
    def recipient(self):
        if "signature" in self._data["tuStatus"][0]:
            return self._data["tuStatus"][0]["signature"]["value"]

    @property
    def references(self):
        references = {}
        for info in self._data["tuStatus"][0]["references"]:
            if info["type"] == "GLSREF":
                references["customer_id"] = info["value"]
            elif info["type"] == "CUSTREF":
                if info["name"] == "Customer's own reference number":
                    references["shipment"] = info["value"]
                elif info["name"] == "Customers own reference number - per TU":
                    references["parcel"] = info["value"]

    @property
    def events(self):
        if not "history" in self._data["tuStatus"][0]:
            return []

        events = []

        for event in self._data["tuStatus"][0]["history"]:
            descr = event["evtDscr"]
            when = datetime.datetime.strptime(event["date"] + event["time"], "%Y-%m-%d%H:%M:%S")
            location = Location(event["address"])

            if descr == "Delivered":
                pe = DeliveryEvent(
                    when=when,
                    location=location,
                    recipient=self.recipient
                )
            elif descr == "Delivered Handed over to neighbour":
                pe = DeliveryNeighbourEvent(
                    when=when,
                    location=location,
                    recipient=self.recipient
                )
            elif descr == "Delivered without proof of delivery":
                pe = DeliveryDropOffEvent(
                    when=when,
                    location=location,
                )
            elif descr == "Out for delivery on GLS vehicle":
                pe = InDeliveryEvent(
                    when=when,
                    location=location
                )
            # GLS rarely does outbound sort scans/events. This makes the
            # tracking data very confusing because one would expect an outbound
            # scan for each inbound scan. Additionally, GLS often has duplicate
            # inbound scans. To avoid confusion, all inbound sort events are
            # simply parsed as "regular" sort events.
            elif descr in (
                "Inbound to GLS location",
                "Inbound to GLS location sorted as Business-Small Parcel",
                "Inbound to GLS location manually sorted",
            ):
                pe = SortEvent(
                    when=when,
                    location=location
                )
            elif descr == "Outbound from GLS location":
                pe = OutboundSortEvent(
                    when=when,
                    location=location
                )
            elif descr == "Not delivered because consignee not in":
                pe = RecipientUnavailableEvent(
                    when=when,
                    location=location
                )
            elif descr == "Consignee contacted Notification card":
                pe =  RecipientNotificationEvent(
                    notification="card",
                    when=when,
                    location=location
                )
            elif descr in (
                "Delivered to a GLS Parcel Shop",
                "Inbound to GLS location to a GLS Parcel Shop",
            ):
                if "parcelShop" in self._data["tuStatus"][0]:
                    location = Store.from_id(self._data["tuStatus"][0]["parcelShop"].get("psID"))
                pe = StoreDropoffEvent(
                    when=when,
                    location=location
                )
            elif descr == "Information transmitted, no shipment available now":
                pe = DataReceivedEvent(
                    when=when
                )
            elif descr == "Forwarded Redirected":
                pe = RedirectEvent(
                    when=when
                )
            elif descr == "Stored" or \
                descr.startswith("Retained at GLS location due to ") or \
                descr.startswith("Stored due to"):
                pe = StoredEvent(
                    when=when,
                    location=location
                )
            elif descr in (
                "Not delivered due to a wrong address",
                "Not out for delivery due to a wrong address",
                ):
                pe = WrongAddressEvent(
                    when=when,
                    location=location
                )
            elif descr == "Not delivered due to declined acceptance":
                pe = DeliveryRefusedEvent(
                    when=when,
                    location=location
                )
            elif descr == "Not delivered Parcel Shop storage term is exceeded":
                pe = StoreNotPickedUpEvent(
                    when=when,
                    location=location
                )
            elif descr == "Returned to consignor":
                pe = ReturnEvent(
                    when=when,
                    location=location
                )
            elif descr == "Data erased from GLS system":
                pe = CancelledEvent(
                    when=when
                )
            else:
                pe = ParcelEvent(
                    when=when
                )

            events.append(pe)

        return list(reversed(events))

    @staticmethod
    def check_digit(tracking_number):
        """
        Calculates the check digit for the given tracking number.

        See chapter 3.2.1 in
        https://gls-group.eu/DE/media/downloads/GLS_Uni-Box_TechDoku_2D_V0110_01-10-2012_DE-download-4424.pdf
        """
        check_digit = 10 - ((sum(itertools.starmap(operator.mul, zip(itertools.cycle((3, 1)), map(int, str(tracking_number))))) + 1) % 10)
        if check_digit == 10:
            check_digit = 0
        return check_digit
