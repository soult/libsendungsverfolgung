import datetime
import json
import re
import requests
import time

from . import base
from .events import *

class Location(base.Location):

    def __init__(self, city):
        match = re.match(r"^(.+) \(([A-Z]{2})\)$", city)
        if not match:
            raise ValueError("Invalid location: %s" % city)
        super(Location, self).__init__(city=match.group(1), country_code=match.group(2))

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
        print(json.dumps(self._data, indent=4, sort_keys=True))

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
            try:
                location = Location(event["city"])
            except ValueError:
                pass

            label = event["contents"][0]["label"]

            if label in (
                "Order information has been transmitted to DPD.",
                "The data of your delivery specifications has been transmitted.",
            ):
                events.append(DataReceivedEvent(
                    when=when
                ))
            elif label in("In transit.", "At parcel delivery centre."):
                events.append(SortEvent(
                    when=when,
                    location=location
                ))
            elif label == "Out for delivery.":
                events.append(InDeliveryEvent(
                    when=when,
                    location=location
                ))
            elif label == "Unfortunately we have not been able to deliver your parcel.":
                if len(event["contents"]) > 1:
                    label2 = event["contents"][1]["label"]
                    if label2 == "Consignee not located, notification has been left.":
                        events.append(RecipientUnavailableEvent(
                            when=when,
                            location=location
                        ))
                        events.append(RecipientNotificationEvent(
                            "notification",
                            when=when,
                            location=location
                        ))
                    elif label2 == "Consignee address not correct.":
                        events.append(WrongAddressEvent(
                            when=when,
                            location=location
                        ))
                    elif label2.startswith("Refusal to accept delivery"):
                        events.append(DeliveryRefusedEvent(
                            when=when,
                            location=location
                        ))
                    else:
                        events.append(FailedDeliveryEvent(
                            when=when,
                            location=location
                        ))
                else:
                    events.append(FailedDeliveryEvent(
                        when=when,
                        location=location
                    ))
            elif label in (
                "We're sorry but your parcel couldn't be delivered as arranged.",
                "Back at parcel delivery centre after an unsuccessful delivery attempt.",
            ):
                events.append(InboundSortEvent(
                    when=when,
                    location=location
                ))
            elif label == "Delivered.":
                if len(event["contents"]) > 1:
                    label2 = event["contents"][1]["label"]
                    if label2 in (
                        "Delivery / general authorisation to deposit.",
                        "Delivery / one-off authorisation to deposit.",
                    ):
                        events.append(DeliveryDropOffEvent(
                            when=when,
                            location=location
                        ))
                    else:
                        events.append(DeliveryEvent(
                            when=when,
                            location=location,
                            recipient=None
                        ))
                else:
                    events.append(DeliveryEvent(
                        when=when,
                        location=location,
                        recipient=None
                    ))
            elif label == "Transfer to DPD ParcelShop by DPD driver.":
                events.append(StoreDropoffEvent(
                    when=when,
                    location=location
                ))
            elif label == "Pick-up from the DPD ParcelShop by DPD driver":
                events.append(StorePickupEvent(
                    when=when,
                    location=location,
                ))
            elif label == "Picked up from DPD ParcelShop by consignee.":
                events.append(DeliveryEvent(
                    when=when,
                    location=location,
                    recipient=None
                ))
            elif label == "Collected by consignee from DPD ParcelShop.":
                if len(event["contents"]) > 1:
                    label2 = event["contents"][1]["label"]
                    if label2 in (
                        "Delivery / general authorisation to deposit.",
                        "Delivery / one-off authorisation to deposit.",
                    ):
                        events.append(DeliveryDropOffEvent(
                            when=when,
                            location=location
                        ))
                    else:
                        events.append(DeliveryEvent(
                            when=when,
                            location=location,
                            recipient=None
                        ))

            else:
                events.append(ParcelEvent(
                    when=when
                ))

        return events
