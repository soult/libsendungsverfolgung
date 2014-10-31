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
#        import json
#        print(json.dumps(data, indent=4, sort_keys=True))

        weight = None
        product = None
        infos = data["tuStatus"][0]["infos"]
        for info in data["tuStatus"][0]["infos"]:
            if info["type"] == "WEIGHT":
                assert info["value"][-3:] == " kg"
                weight = float(info["value"][:-3])
            elif info["type"] == "PRODUCT":
                product = info["value"]

        events = reversed(list(map(cls.parse_event, data["tuStatus"][0]["history"])))

        return base.Parcel(cls, tracking_number, events, product, weight)

    @classmethod
    def parse_event(cls, event):
        when = datetime.datetime.strptime(event["date"] + event["time"], "%Y-%m-%d%H:%M:%S")
        location = event["address"]

        if event["evtDscr"] == "Delivered":
            event = base.DeliveryEvent(
                when=when,
                location=location,
                recipient=None
            )
        elif event["evtDscr"] == "Out for delivery on GLS vehicle":
            event = base.InDeliveryEvent(
                when=when,
                location=location
            )
        elif event["evtDscr"] in ("Inbound to GLS location", "Inbound to GLS location sorted as Business-Small Parcel"):
            event = base.SortEvent(
                when=when,
                location=location
            )
        else:
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
