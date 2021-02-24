import dateutil.parser
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

    DAYS = ("Mo", "Tu", "We", "Th", "Fr", "Sa", "Su")

    def __init__(self, store_id):
        r = requests.get("https://tracking.dpd.de/rest/ps/en_US/" + store_id)
        data = r.json()["getParcelShopByIdResponse"]["parcelShop"]

        super(Store, self).__init__(
            name=data["company"],
            address="%s %s" % (data["street"], data["houseNo"]),
            postcode=data["zipCode"],
            city=data["city"],
            country_code=data["country"],
            opening_hours=self._parse_opening_hourse(data["openingHours"]),
            phone=data.get("contactPersonPhone"),
            email=data.get("contactPersonEmail"),
        )

    def _parse_opening_hourse(self, data):
        result = []

        for day in data:
            if day["dayOff"]:
                continue

            if day["closeMorning"] == day["openAfternoon"]:
                result.append("%s %s-%s" % (
                    self.DAYS[day["weekdayNum"] - 1],
                    day["openMorning"],
                    day["closeAfternoon"],
                ))
            elif day["openMorning"] == "00:00" and day["closeMorning"] == "00:00":
                result.append("%s %s-%s" % (
                    self.DAYS[day["weekdayNum"] - 1],
                    day["openAfternoon"],
                    day["closeAfternoon"],
                ))
            else:
                result.append("%s %s-%s, %s-%s" % (
                    self.DAYS[day["weekdayNum"] - 1],
                    day["openMorning"],
                    day["closeMorning"],
                    day["openAfternoon"],
                    day["closeAfternoon"],
                ))

        return "; ".join(result)


class Parcel(base.Parcel):

    COMPANY_IDENTIFIER = "dpd"
    COMPANY_NAME = "Dynamic Parcel Distribution"
    COMPANY_SHORTNAME = "DPD"

    POSTCODE_LENGTHS = {
        40: 4,
        276: 5,
    }

    def __init__(self, tracking_number, postcode=None, *args, **kwargs):
        if len(tracking_number) == 28 and tracking_number[0] == "%":
            self._barcode = tracking_number
            self._tracking_number = self._barcode[8:22]
            country = int(tracking_number[-3:])
            postcode_length = self.POSTCODE_LENGTHS.get(country, 7)
            self._postcode = tracking_number[(8-postcode_length):8]
        else:
            self._barcode = None
            self._tracking_number = str(tracking_number)
            self._postcode = postcode
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
        url = "https://tracking.dpd.de/rest/plc/en_US/" + str(self.tracking_number)
        if self._postcode:
            url += "/" + str(self._postcode)
        r = requests.get(url, timeout=base.TIMEOUT)

        data = r.json()
        assert "parcellifecycleResponse" in data
        if data["parcellifecycleResponse"]["parcelLifeCycleData"] is None:
            raise base.UnknownParcelException()

        self._data = data["parcellifecycleResponse"]["parcelLifeCycleData"]

    @property
    def tracking_number(self):
        return self._tracking_number

    @property
    def tracking_link(self):
        return "https://extranet.dpd.de/status/en_DE/parcel/" + self.tracking_number

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
        elif self.product_id == "384":
            return "Next Day"
        elif self.product_id == "817":
            return "Postübergabe"

        self.fetch_data()
        return self._data["shipmentInfo"]["productName"]

    @property
    def is_express(self):
        return self.product_id in ("179", "225", "228", "299")

    @property
    def is_cash_on_delivery(self):
        return self.product_id in ("109", "113", "128", "132", "140", "142", "150", "152", "158", "161", "171")

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
            if code in ("1", "2"):
                events.append((SortEvent(
                    when=when,
                    location=location,
                )))
            elif code == "3":
                events.append(InDeliveryEvent(
                    when=when,
                    location=location,
                ))
            elif code == "4":
                events.append(InboundSortEvent(
                    when=when,
                    location=location,
                ))
            elif code == "5":
                events.append(InboundSortEvent(
                    when=when,
                    location=location,
                ))
            elif code == "8":
                if event["scanData"]["additionalCodes"]:
                    for additional_code in event["scanData"]["additionalCodes"]["additionalCode"]:
                        if additional_code["code"] == "011":
                            events.append(WrongAddressEvent(
                                when=when,
                                location=location
                            ))
                            break
            elif code == "10":
                events.append(SortEvent(
                    when=when,
                    location=location,
                ))
            elif code == "13":
                recipient = None
                if "additionalProperties" in self._data["shipmentInfo"]:
                    for property in self._data["shipmentInfo"]["additionalProperties"]:
                        if property["key"] == "RECEIVER_NAME":
                            recipient = property["value"]
                            break

                special_delivery = False
                if event["scanData"].get("additionalCodes"):
                    for additional_code in event["scanData"]["additionalCodes"]["additionalCode"]:
                        if additional_code["code"] in ("068", "069"):
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
                        recipient=recipient,
                    ))
            elif code == "14":
                if event["scanData"]["additionalCodes"]:
                    for additional_code in event["scanData"]["additionalCodes"]["additionalCode"]:
                        if additional_code["code"] == "011":
                            events.append(WrongAddressEvent(
                                when=when,
                                location=location
                            ))
                            break
                        elif additional_code["code"] == "019":
                            events.append(RecipientNotificationEvent(
                                when=when,
                                location=location,
                                notification="first notification"
                            ))
                        elif additional_code["code"] == "091":
                            events.append(RecipientNotificationEvent(
                                when=when,
                                location=location,
                                notification="parcelshop delivery"
                            ))
                    else:
                        events.append(RecipientUnavailableEvent(
                            when=when,
                            location=location,
                        ))
            elif code == "15":
                events.append(PickupEvent(
                    when=when,
                    location=location,
                ))
            elif code == "18":
                scan_type = event["scanData"]["scanType"]["name"]
                if scan_type == "ShipmentDataTransferred":
                    events.append(DataReceivedEvent(
                        when=when,
                    ))
                elif scan_type == "RedirectionConfirmationDocument":
                    events.append(RedirectEvent(
                        when=when,
                    ))
            elif code == "23":
                store_id = [x["value"] for x in event["links"][0]["queryParameters"] if x["key"] == "ParcelShopId"][0]
                events.append(StoreDropoffEvent(
                    when=when,
                    location=Store(store_id),
                ))


        return events
