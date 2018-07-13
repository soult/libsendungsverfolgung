import datetime
import itertools
import operator

from . import base
from .events import *

class Parcel(base.Parcel):

    COMPANY_IDENTIFIER = "at.post"
    COMPANY_NAME = "Österreichische Post AG"
    COMPANY_SHORTNAME = "Post.AT"

    def __init__(self, tracking_number, *args, **kwargs):
        self._tracking_number = str(tracking_number)
        self._data = None

    @classmethod
    def from_barcode(cls, barcode):
        if barcode.isnumeric() and len(barcode) in (16, 22):
            if str(cls.check_digit(barcode[:-1])) == barcode[-1]:
                return cls(barcode)

    @staticmethod
    def check_digit(tracking_number):
        """
        Calculates the check digit for the given tracking number.

        https://www.post.at/downloads/BelabelungAvisodatenFibel_V5.1.pdf
        chapter 4.1.6
        """
        check_digit = 10 - ((sum(itertools.starmap(operator.mul, zip(itertools.cycle((3, 1)), map(int, tracking_number))))) % 10)
        if check_digit == 10:
            check_digit = 0
        return check_digit

    @property
    def tracking_number(self):
        return self._tracking_number

    @property
    def tracking_link(self):
        return "https://www.post.at/sendungsverfolgung.php/details?pnum1=" + self.tracking_number

    @property
    def product(self):
        """
        Returns the product name.

        https://www.post.at/downloads/BelabelungAvisodatenFibel_V5.1.pdf
        chapter 4.1.4
        """
        if len(self.tracking_number) == 16:
            product_id = self.tracking_number[4:6]
        elif len(self.tracking_number) == 22:
            product_id = self.tracking_number[15:17]

        if product_id == "01":
            return "Paket Österreich"
        elif product_id == "02":
            return "Paket Premium select Österreich"
        elif product_id == "03":
            return "Premium light"
        elif product_id == "05":
            return "Paket Österreich Postfiliale"
        elif product_id == "07":
            return "Retourpaket"
        elif product_id == "08":
            return "Paket Premium Österreich/Int. Outbound B2B"
        elif product_id == "10":
            return "EMS Österreich/International Outbound"
        elif product_id == "12":
            return "Combi-freight Österreich/Int. Outbound"
        elif product_id == "29":
            return "Same Day"
        elif product_id == "30":
            return "Next Day"
        elif product_id == "33":
            return "Päckchen M"
        elif product_id == "36":
            return "Paket Light International Outbound"
        elif product_id == "39":
            return "Paket Plus International Outbound"

