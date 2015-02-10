import datetime
import json
import requests
import time

from . import base

class DPD(object):

    SLUG = "dpd"
    SHORTNAME = "DPD"
    NAME = "Dynamic Parcel Distribution"

    @classmethod
    def get_parcel(cls, tracking_number):
        params = {
            "parcelNr": str(tracking_number),
            "locale": "en",
            "type": "1",
            "jsoncallback": "_jqjsp",
            "_%i" % int(time.time() * 1000): "",
        }
        r = requests.get("https://tracking.dpd.de/cgi-bin/simpleTracking.cgi", params=params)

        data = json.loads(r.text[7:-1])

        if "ErrorJSON" in data:
            if data["ErrorJSON"]["code"] == -8:
                raise ValueError("Unknown tracking number")
            raise Exception("Unknown error")

        tracking_number = data["TrackingStatusJSON"]["shipmentInfo"]["parcelNumber"]
        product = data["TrackingStatusJSON"]["shipmentInfo"]["product"]

        events = list(map(cls.parse_event, data["TrackingStatusJSON"]["statusInfos"]))

        return base.Parcel(cls, tracking_number, events, product, None, None)

    @classmethod
    def parse_event(cls, event):
        when = datetime.datetime.strptime(event["date"] + event["time"], "%d-%m-%Y%H:%M ")
        location = event["city"]

        label = event["contents"][0]["label"]

        if label == "Order information has been transmitted to DPD.":
            event = base.DataReceivedEvent(
                when=when
            )
        elif label in("In transit.", "At parcel delivery centre."):
            event = base.SortEvent(
                when=when,
                location=location
            )
        elif label == "Out for delivery.":
            event = base.InDeliveryEvent(
                when=when,
                location=location
            )
        elif label == "Unfortunately we have not been able to deliver your parcel.":
            event = base.FailedDeliveryEvent(
                when=when,
                location=location
            )
        elif label == "Delivered.":
            event = base.DeliveryEvent(
                when=when,
                location=location,
                recipient=None
            )
        else:
            print(event)
            event = base.ParcelEvent(
                when=when
            )

        return event

    @classmethod
    def autodetect(cls, tracking_number, country, postcode):
        if len(tracking_number) == 14:
            return cls.get_parcel(tracking_number)
