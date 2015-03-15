import datetime
import json
import requests
import time

from . import base
from .events import *

class Parcel(base.Parcel):

    def __init__(self, tracking_number, *args, **kwargs):
        tracking_number = str(tracking_number)
        if len(tracking_number) != 14:
            raise ValueError("Invalid tracking number")
        self._get_data(tracking_number)

    def _get_data(self, tracking_number):
        params = {
            "parcelNr": str(tracking_number),
            "locale": "en",
            "type": "1",
            "jsoncallback": "_jqjsp",
            "_%i" % int(time.time() * 1000): "",
        }
        r = requests.get("https://tracking.dpd.de/cgi-bin/simpleTracking.cgi", params=params)

        self._data = json.loads(r.text[7:-1])

        if "ErrorJSON" in self._data:
            if self._data["ErrorJSON"]["code"] == -8:
                raise ValueError("Unknown tracking number")
            raise Exception("Unknown error")

    @property
    def tracking_number(self):
        return self._data["TrackingStatusJSON"]["shipmentInfo"]["parcelNumber"]

    @property
    def product(self):
        return self._data["TrackingStatusJSON"]["shipmentInfo"]["product"]

    @property
    def events(self):
        events = []

        for event in self._data["TrackingStatusJSON"]["statusInfos"]:
            when = datetime.datetime.strptime(event["date"] + event["time"], "%d-%m-%Y%H:%M ")
            location = event["city"]

            label = event["contents"][0]["label"]

            if label == "Order information has been transmitted to DPD.":
                pe = DataReceivedEvent(
                    when=when
                )
            elif label in("In transit.", "At parcel delivery centre."):
                pe = SortEvent(
                    when=when,
                    location=location
                )
            elif label == "Out for delivery.":
                pe = InDeliveryEvent(
                    when=when,
                    location=location
                )
            elif label == "Unfortunately we have not been able to deliver your parcel.":
                pe = FailedDeliveryEvent(
                    when=when,
                    location=location
                )
            elif label == "Delivered.":
                pe = DeliveryEvent(
                    when=when,
                    location=location,
                    recipient=None
                )
            else:
                pe = ParcelEvent(
                    when=when
                )

            events.append(pe)

        return events
