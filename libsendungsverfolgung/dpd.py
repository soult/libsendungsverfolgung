import datetime
import html.parser
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

class Store(base.Store):

    class StoreHTMLParser(html.parser.HTMLParser):

        STATE_START = 2**0
        STATE_IDLE = 2**1
        STATE_SECTION = 2**2
        STATE_SECTION_HEADING = 2**3
        STATE_ROW = 2**4
        STATE_CELL = 2**5

        STATE_ADDRESS = 2**6
        STATE_CONTACT = 2**7
        STATE_OPENING_HOURS = 2**8

        def __init__(self, *args, **kwargs):
            super(Store.StoreHTMLParser, self).__init__(*args, **kwargs)
            self.state = self.STATE_IDLE

        def _in_state(self, *states):
            state = states[0]
            for s in states[1:]:
                state |= s
            return (self.state & state) == state

        def handle_starttag(self, tag, attrs):
            attrs = dict(attrs)
            if self._in_state(self.STATE_START) and tag == "div" and attrs.get("class") == "parcelShopDetails":
                self.state = self.STATE_IDLE
            elif self._in_state(self.STATE_IDLE) and tag == "div":
                div_class = attrs.get("class")
                if div_class == "address":
                    self.state = self.STATE_ADDRESS
                    self._address = ""
                elif div_class == "contact":
                    self.state = self.STATE_CONTACT
                    self._contact = []
                elif div_class == "opening-hours":
                    self.state = self.STATE_OPENING_HOURS
                    self._opening_hours = []
                self.state |= self.STATE_SECTION
            elif self._in_state(self.STATE_SECTION) and tag == "b":
                self.state = (self.state ^ self.STATE_SECTION) | self.STATE_SECTION_HEADING
            elif self._in_state(self.STATE_SECTION) and tag == "tr":
                self.state = (self.state ^ self.STATE_SECTION) | self.STATE_ROW
                if self._in_state(self.STATE_CONTACT):
                    self._contact.append([])
                elif self._in_state(self.STATE_OPENING_HOURS):
                    self._opening_hours.append([])
            elif self._in_state(self.STATE_ROW) and tag in ("th", "td"):
                self.state = (self.state ^ self.STATE_ROW) | self.STATE_CELL
                if self._in_state(self.STATE_CONTACT):
                    self._contact[-1].append("")
                elif self._in_state(self.STATE_OPENING_HOURS):
                    self._opening_hours[-1].append("")

        def handle_endtag(self, tag):
            if self._in_state(self.STATE_SECTION_HEADING) and tag == "b":
                self.state = (self.state ^ self.STATE_SECTION_HEADING) | self.STATE_SECTION
            elif self._in_state(self.STATE_SECTION) and tag == "div":
                self.state = self.STATE_IDLE
            elif self._in_state(self.STATE_ROW) and tag == "tr":
                self.state = (self.state ^ self.STATE_ROW) | self.STATE_SECTION
            elif self._in_state(self.STATE_CELL) and tag in ("th", "td"):
                self.state = (self.state ^ self.STATE_CELL) | self.STATE_ROW

        def handle_startendtag(self, tag, attrs):
            if self._in_state(self.STATE_SECTION_HEADING):
                return
            if self._in_state(self.STATE_ADDRESS) and tag == "br":
                self._address += "\n"

        def handle_data(self, data):
            if self._in_state(self.STATE_SECTION_HEADING):
                return
            elif self._in_state(self.STATE_ADDRESS):
                self._address += data
            elif self._in_state(self.STATE_CONTACT, self.STATE_CELL):
                self._contact[-1][-1] += data
            elif self._in_state(self.STATE_OPENING_HOURS, self.STATE_CELL):
                self._opening_hours[-1][-1] += data

        def handle_entityref(self, name):
            if self._in_state(self.STATE_ADDRESS) and name == "nbsp":
                self._address += " "

        def get_location(self):
            address_data = self._address.strip().split("\n")
            address = "\n".join(address_data[:-1])

            match = re.match(r"^(.+?) (.+) \(([A-Z]{2})\)$", address_data[-1])
            postcode, city, country_code = match.groups()

            return (address, postcode, city, country_code)

        def get_contact(self):
            phone = email = None

            for k, v in self._contact:
                if k == "Phone:":
                    email = v
                elif k == "Fax:":
                    phone = v

            return (phone, email)

        def get_opening_hours(self):
            opening_hours = []
            for row in self._opening_hours:
                if row[1] == "closed":
                    continue
                day, before_noon, afternoon = row
                assert day[:2] in ("Mo", "Tu", "We", "Th", "Fr", "Sa", "Su")
                if before_noon[-5:] == afternoon[:5]:
                    opening_hours.append("%s %s-%s" % (day[:2], before_noon[:5], afternoon[-5:]))
                else:
                    opening_hours.append("%s %s,%s" % (day[:2], before_noon, afternoon))
            return "; ".join(opening_hours)

    def __init__(self, label, content):
        parser = self.StoreHTMLParser()
        parser.feed(content)

        name = label
        address, postcode, city, country_code = parser.get_location()
        opening_hours = parser.get_opening_hours()
        phone, email = parser.get_contact()

        super(Store, self).__init__(
            name=name,
            address=address,
            postcode=postcode,
            city=city,
            country_code=country_code,
            opening_hours=opening_hours,
            phone=phone,
            email=email
        )

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
        r = requests.get("https://tracking.dpd.de/cgi-bin/simpleTracking.cgi", params=params, verify=False)

        self._data = json.loads(r.text[7:-1])

        if "ErrorJSON" in self._data:
            if self._data["ErrorJSON"]["code"] == -8:
                raise ValueError("Unknown tracking number")
            raise Exception("Unknown error")

    @property
    def recipient(self):
        """
        DPD has this weird policy where you have to send the postal code to get
        the recipient's name in the simpleTracking.cgi JSON format. But in
        other HTML pages, you can find it without any restrictions.
        """
        params = {
            "pknr": self.tracking_number,
            "locale": "en",
            "typ": "2",
        }
        r = requests.get("https://tracking.dpd.de/cgi-bin/delistrack", params=params, verify=False)
        match = re.search(r"<br>Delivered to: (.+?)&nbsp;</td>", r.text)
        if not match:
            return None

        hp = html.parser.HTMLParser()
        return hp.unescape(match.group(1))

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
            event_time = event["time"]
            if event_time == "-":
                event_time = "23:59 "
            when = datetime.datetime.strptime(event["date"] + event_time, "%d-%m-%Y%H:%M ")
            try:
                location = Location(event["city"])
            except ValueError:
                pass

            if len(event["contents"]) == 0:
                continue

            label = event["contents"][0]["label"]

            if label in (
                "Order information has been transmitted to DPD.",
                "The data of your delivery specifications has been transmitted.",
            ):
                events.append(DataReceivedEvent(
                    when=when
                ))
            elif label == "Parcel handed to Pickup parcelshop by consignor.":
                events.append(PostedEvent(
                    when=when,
                    location=location
                ))
            elif label == "Pick-up from the Pickup parcelshop by DPD driver":
                for content in event["contents"][1:]:
                    if content["contentType"] == "modal":
                        location = Store(content["label"], content["content"])
                        events.append(StorePickupEvent(
                            when=when,
                            location=location
                        ))
                        break
                else:
                    events.append(StorePickupEvent(
                        when=when,
                        location=location
                    ))
            elif label in("In transit.", "At parcel delivery centre."):
                events.append(SortEvent(
                    when=when,
                    location=location
                ))
                if len(event["contents"]) > 1:
                    label2 = event["contents"][1]["label"]
                    if label2 == "Consignee address not correct.":
                        events.append(WrongAddressEvent(
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
            elif label == "Back at parcel delivery centre after an unsuccessful delivery attempt.":
                events.append(InboundSortEvent(
                    when=when,
                    location=location
                ))
            elif label == "We're sorry but your parcel couldn't be delivered as arranged.":
                if len(event["contents"]) > 1:
                    label2 = event["contents"][1]["label"]
                    if label2 == "Return to consignor after unsuccessful delivery to third party.":
                        events.append(ReturnEvent(
                            when=when,
                            location=location
                        ))
                    elif label2 == "Consignee address not correct.":
                        events.append(WrongAddressEvent(
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
                            recipient=self.recipient
                        ))
                else:
                    events.append(DeliveryEvent(
                        when=when,
                        location=location,
                        recipient=self.recipient
                    ))
            elif label == "Transfer to Pickup parcelshop by DPD driver.":
                for content in event["contents"][1:]:
                    if content["contentType"] == "modal":
                        location = Store(content["label"], content["content"])
                        events.append(StoreDropoffEvent(
                            when=when,
                            location=location
                        ))
                        break
                else:
                    events.append(StoreDropoffEvent(
                        when=when,
                        location=location
                    ))
            elif label == "Pick-up from the Pickup parcelshop by DPD driver":
                events.append(StorePickupEvent(
                    when=when,
                    location=location,
                ))
            elif label == "Collected by consignee from Pickup parcelshop." or \
                label == "Picked up from Pickup parcelshop by consignee.":
                events.append(DeliveryEvent(
                    when=when,
                    location=location,
                    recipient=None
                ))
            elif label == "Collected by consignee from Pickup parcelshop.":
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
