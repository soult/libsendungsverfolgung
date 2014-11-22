import datetime
import itertools
import operator
import requests
import time

from . import base

class GLS(object):

    SLUG = "gls"
    SHORTNAME = "GLS"
    NAME = "General Logistics Systems"

    @classmethod
    def get_parcel(cls, tracking_number):
        tracking_number = str(tracking_number)
        if len(tracking_number) == 11:
            tracking_number += str(cls.check_digit(tracking_number))
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

        data = r.json()

        weight = None
        product = None
        infos = data["tuStatus"][0]["infos"]
        for info in data["tuStatus"][0]["infos"]:
            if info["type"] == "WEIGHT":
                assert info["value"][-3:] == " kg"
                weight = float(info["value"][:-3])
            elif info["type"] == "PRODUCT":
                product = info["value"]

        references = {}
        for info in data["tuStatus"][0]["references"]:
            if info["type"] == "GLSREF":
                references["customer_id"] = info["value"]
            elif info["type"] == "CUSTREF":
                if info["name"] == "Customer's own reference number":
                    references["shipment"] = info["value"]
                elif info["name"] == "Customers own reference number - per TU":
                    references["parcel"] = info["value"]

        events = reversed(list(map(cls.parse_event, data["tuStatus"][0]["history"])))

        return base.Parcel(cls, tracking_number, events, product, weight, references)

    @classmethod
    def parse_event(cls, event):
        when = datetime.datetime.strptime(event["date"] + event["time"], "%Y-%m-%d%H:%M:%S")
        location = event["address"]["city"] + ", " + event["address"]["countryCode"]

        if event["evtDscr"] == "Delivered":
            event = base.DeliveryEvent(
                when=when,
                location=location,
                recipient=None
            )
        elif event["evtDscr"] == "Delivered Handed over to neighbour":
            event = base.DeliveryNeighbourEvent(
                when=when,
                location=location,
                recipient=None
            )
        elif event["evtDscr"] == "Delivered without proof of delivery":
            event = base.DeliveryDropOffEvent(
                when=when,
                location=location,
            )
        elif event["evtDscr"] == "Out for delivery on GLS vehicle":
            event = base.InDeliveryEvent(
                when=when,
                location=location
            )
        elif event["evtDscr"] in ("Inbound to GLS location", "Inbound to GLS location sorted as Business-Small Parcel", "Outbound from GLS location", "Inbound to GLS location manually sorted"):
            event = base.SortEvent(
                when=when,
                location=location
            )
        elif event["evtDscr"] == "Not delivered because consignee not in":
            event = base.RecipientUnavailableEvent(
                when=when,
                location=location
            )
        elif event["evtDscr"] == "Consignee contacted Notification card":
            event = base.RecipientNotificationEvent(
                notification="card",
                when=when,
                location=location
            )
        elif event["evtDscr"] == "Delivered to a GLS Parcel Shop":
            event = base.StoreDropoffEvent(
                when=when,
                location=location
            )
        elif event["evtDscr"] == "Information transmitted, no shipment available now":
            event = base.DataReceivedEvent(
                when=when
            )
        elif event["evtDscr"] == "Stored" or event["evtDscr"].startswith("Retained at GLS location"):
            event = base.StoredEvent(
                when=when,
                location=location
            )
        elif event["evtDscr"] == "Not delivered due to a wrong address":
            event = base.WrongAddressEvent(
                when=when,
                location=location
            )
        elif event["evtDscr"] == "Not delivered due to declined acceptance":
            event = base.DeliveryRefusedEvent(
                when=when,
                location=location
            )
        elif event["evtDscr"] == "Not delivered Parcel Shop storage term is exceeded":
            event = base.StoreNotPickedUpEvent(
                when=when,
                location=location
            )
        elif event["evtDscr"] == "Returned to consignor":
            event = base.ReturnEvent(
                when=when,
                location=location
            )
        elif event["evtDscr"] == "Data erased from GLS system":
            event = base.CancelledEvent(
                when=when
            )
        else:
            print(event)
            event = base.ParcelEvent(
                when=when
            )

        return event

    @classmethod
    def autodetect(cls, tracking_number, country, postcode):
        if len(tracking_number) == 11:
            tracking_number += str(cls.check_digit(tracking_number))
        if len(tracking_number) == 12:
            try:
                check_digit = cls.check_digit(tracking_number[:11])
                if check_digit == int(tracking_number[11]):
                    return cls.get_parcel(tracking_number)
            except ValueError:
                pass
        return None

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
