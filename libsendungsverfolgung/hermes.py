import datetime
import json
import random
import requests
import time

from . import base
from .events import *

API_KEY = "1d155daa6173ddef89039f55b78b9f4812ec9d9384c7adeff7836bee91da5a550b424c349368d8843790ccf7649402d0"

class Location(base.Location):
    pass

class Store(base.Store):
    pass

class Parcel(base.Parcel):

    def __init__(self, tracking_number, *args, **kwargs):
        tracking_number = str(tracking_number)
        if len(tracking_number) != 14:
            raise ValueError("Invalid tracking number")
        self._get_data(tracking_number)

    def _get_data(self, tracking_number):
        params = {
            "callback": "jQuery1720%i_%i" % (random.randrange(10**15, 10**16), time.time() * 1000),
            "id": tracking_number,
            "lng": "en",
            "token": API_KEY,
            "_": str(int(time.time() * 1000))
        }
        r = requests.get("https://tracking.hermesworld.com/SISYRestAPIWebApp/V1/sisy-rs/GetHistoryByID", params=params)

        self._data = json.loads(r.text[41:-2])

    @property
    def tracking_number(self):
        return self._data["status"][0]["shipmentID"]

    @property
    def events(self):
        events = []

        for event in self._data["status"]:
            status = event["statusDescription"].strip()
            when = datetime.datetime.strptime(event["statusDate"] + event["statusTime"], "%d.%m.%Y%H:%M:%S")

            if status == "The parcel has been announced electronically to Hermes.":
                events.append(DataReceivedEvent(when))
            elif status == "Parcel has left the client\u2019s warehouse":
                events.append(PickupEvent(None, when))
            elif status == "The parcel has been received by the Hermes Parcel Shop.":
                events.append(PostedEvent(None, when))
            elif status == "The parcel has been picked-up at the Hermes ParcelShop and sorted for further shipment.":
                events.append(PickupEvent(None, when))
            elif status.startswith("The parcel has been sorted / "): # AT
                location = base.Location(city=status[29:], country_code="AT")
                events.append(SortEvent(location, when))
            elif status.startswith("The parcel is located at the Hermes depot "): # DE
                location = base.Location(city=status[42:-1], country_code="DE")
                events.append(SortEvent(location, when))
            elif status.startswith("The parcel has been received by Hermes depot "): # DE
                location = base.Location(city=status[45:], country_code="DE")
                events.append(SortEvent(location, when))
            elif status.startswith("The parcel has been received at the Hermes depot "): # DE
                location = base.Location(city=status[49:], country_code="DE")
                events.append(SortEvent(location, when))
            elif status == "The parcel has been sorted at a Hermes Logistic Hub.":
                location = base.Location(name="Hermes Logistic Hub", country_code="DE")
                events.append(SortEvent(location, when))
            elif status == "The Parcel is out for delivery today" or \
                    status == "\"The parcel is out for delivery":
                location = base.Location(country_code=event["countryCode"])
                events.append(InDeliveryEvent(location, when))
            elif status == "The parcel has been delivered.":
                location = base.Location(postcode=event["zipCode"], city=event["city"], country_code=event["countryCode"])
                events.append(DeliveryEvent(None, location, when))
            else:
                events.append(ParcelEvent(when))

        return list(reversed(events))
