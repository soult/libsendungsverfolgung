import datetime
import dateutil.parser
import decimal
import html.parser
import json
import re
import requests

from . import base
from .events import *

class Location(base.Location):

    def __init__(self, city):
        match = re.match(r"^(.+) \(([A-Z]{2})\)$", city)
        if match:
            super(Location, self).__init__(city=match.group(1), country_code=match.group(2))
        else:
            super(Location, self).__init__(city=city)

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
            address = "\n".join(address_data)

            match = re.match(r"^(.+?)\s(.+)\s\(([A-Z]{2})\)$", address_data[-1])
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

    COMPANY_IDENTIFIER = "dpd"
    COMPANY_NAME = "Dynamic Parcel Distribution"
    COMPANY_SHORTNAME = "DPD"

    def __init__(self, tracking_number, *args, **kwargs):
        if len(tracking_number) == 28 and tracking_number[0] == "%":
            self._barcode = tracking_number
            self._tracking_number = self._barcode[8:22]
        else:
            self._barcode = None
            self._tracking_number = str(tracking_number)
        self._data = None

    @classmethod
    def from_barcode(cls, barcode):
        if len(barcode) == 28 and barcode[0] == "%":
            return cls(barcode)
        elif len(barcode) == 27 and str.isdigit(barcode):
            return cls("%" + barcode)

    def fetch_data(self):
        if self._data:
            return
        r = requests.get("https://tracking.dpd.de/rest/plc/en_US/" + str(self.tracking_number), timeout=base.TIMEOUT)

        data = r.json()
        assert "parcellifecycleResponse" in data
        if data["parcellifecycleResponse"]["parcelLifeCycleData"] is None:
            raise base.UnknownParcelException()

        self._data = data["parcellifecycleResponse"]["parcelLifeCycleData"]

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
        r = requests.get("https://tracking.dpd.de/cgi-bin/delistrack", params=params, verify=False, timeout=base.TIMEOUT)
        match = re.search(r"<br>Delivered to: (.+?)&nbsp;</td>", r.text)
        if not match:
            return None

        hp = html.parser.HTMLParser()
        return hp.unescape(match.group(1))

    @property
    def tracking_number(self):
        return self._tracking_number

    @property
    def product_id(self):
        if self._barcode:
            return self._barcode[22:25]
        self.fetch_data()
        return self._data["shipmentInfo"]["serviceCode"]

    @property
    def product(self):
        """
        Returns the product name.

        ftp://ftp.dpd-business.at/Datenspezifikationen/DE/gbs_V3.3.1_module_statusreporting.pdf
        chapter 9.3
        """
        # Only look up product if we don't have barcode or don't know the encoded product
        if self.product_id in ("101", "120"):
            return "Normalpaket"
        elif self.product_id == "102":
            return "Normalpaket, Gefahrgut"
        elif self.product_id in ("105", "124"):
            return "Normalpaket, unfrei"
        elif self.product_id in ("109", "128"):
            return "Normalpaket, Nachnahme"
        elif self.product_id in ("113", "132"):
            return "Normalpaket, Austauschpaket"
        elif self.product_id == "117":
            return "Normalpaket, Mitnahmenpaket"
        elif self.product_id == "118":
            return "Normalpaket, Austauschpaket (retour)"
        elif self.product_id in ("136", "146"):
            return "Kleinpaket"
        elif self.product_id in ("138", "148"):
            return "Kleinpaket, unfrei"
        elif self.product_id in ("140", "150"):
            return "Kleinpaket, Nachnahme"
        elif self.product_id in ("142", "152"):
            return "Kleinpaket, Austauschpaket"
        elif self.product_id == "144":
            return "Kleinpaket, Mitnahmenpaket"
        elif self.product_id == "145":
            return "Kleinpaket, Austauschpaket (retour)"
        elif self.product_id == "154":
            return "Parcelletter"
        elif self.product_id in ("155", "168"):
            return "Garantiepaket"
        elif self.product_id in ("158", "171"):
            return "Garantiepaket, unfrei"
        elif self.product_id == "161":
            return "Garantiepaket, Nachnahme"
        elif self.product_id in ("164", "177"):
            return "Garantiepaket, Austauschpaket"
        elif self.product_id == "166":
            return "Garantiepaket, Austauschpaket (retour)"
        elif self.product_id == "179":
            return "Express 10:00"
        elif self.product_id == "225":
            return "Express 12:00"
        elif self.product_id == "228":
            return "Express 12:00 Samstag"
        elif self.product_id == "298":
            return "Retoure an Versender"
        elif self.product_id == "299":
            return "Systemretoure international Express"
        elif self.product_id == "300":
            return "Systemretoure"
        elif self.product_id == "327":
            return "Normalpaket B2C"
        elif self.product_id == "328":
            return "Kleinpaket B2C"
        elif self.product_id == "332":
            return "Retoure"
        elif self.product_id == "365":
            return "Reifenlogistik"
        elif self.product_id == "365":
            return "Reifenlogistik B2C"
        elif self.product_id == "817":
            return "Postübergabe"

        self.fetch_data()
        return self._data["shipmentInfo"]["productName"]

    @property
    def weight(self):
        self.fetch_data()
        for event in self._data["scanInfo"]["scan"]:
            if event["scanData"]["parcelMeasurements"]:
                measurements = event["scanData"]["parcelMeasurements"]
                if measurements["weightGram"]:
                    return decimal.Decimal(measurements["weightGram"]) / decimal.Decimal(1000)

    @property
    def is_express(self):
        return self.product_id in ("179", "225", "228", "299")

    @property
    def events(self):
        self.fetch_data()
        events = []

        for event in self._data["scanInfo"]["scan"]:
            when = dateutil.parser.isoparse(event["date"])
            try:
                location = Location(event["scanData"]["location"])
            except ValueError:
                location = None

            code = event["scanData"]["scanType"]["code"]
            if code in ("01", "02"):
                events.append((SortEvent(
                    when=when,
                    location=location,
                )))
            elif code == "03":
                events.append(InDeliveryEvent(
                    when=when,
                    location=location,
                ))
            elif code == "04":
                events.append(InboundSortEvent(
                    when=when,
                    location=location,
                ))
            elif code == "05":
                events.append(InboundSortEvent(
                    when=when,
                    location=location,
                ))
            elif code == "10":
                events.append(SortEvent(
                    when=when,
                    location=location,
                ))
            elif code == "13":
                special_delivery = False
                if event["scanData"]["additionalCodes"]:
                    for additional_code in event["scanData"]["additionalCodes"]["additionalCode"]:
                        if additional_code["code"] == "068":
                            events.append(DeliveryNeighbourEvent(
                                when=when,
                                location=location,
                                recipient=None,
                            ))
                            special_delivery = True
                            break
                        elif additional_code["code"] == "069":
                            events.append(DeliveryDropOffEvent(
                                when=when,
                                location=location
                            ))
                            special_delivery = True
                            break

                if not special_delivery:
                    events.append(DeliveryEvent(
                        when=when,
                        location=location,
                        recipient=None,
                    ))
            elif code == "14":
                events.append(RecipientUnavailableEvent(
                    when=when,
                    location=location,
                ))
                if event["scanData"]["additionalCodes"]:
                    for additional_code in event["scanData"]["additionalCodes"]["additionalCode"]:
                        if additional_code["code"] == "019":
                            events.append(RecipientNotificationEvent(
                                when=when,
                                location=location,
                                notification=additional_code["name"]
                            ))
            elif code == "15":
                events.append(PickupEvent(
                    when=when,
                    location=location,
                ))
            elif code == "18":
                info_container = event["scanData"]["infoContainer"]
                if info_container["infocontainerType"] == "01":
                    events.append(DataReceivedEvent(
                        when=when,
                    ))
                elif info_container["infocontainerType"] == "02":
                    events.append(RedirectEvent(
                        when=when,
                    ))

        return events
