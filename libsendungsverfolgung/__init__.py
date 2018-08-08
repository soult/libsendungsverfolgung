import abc
import collections
import csv
import os.path

__all__ = ["at_post", "base", "events", "dhl", "dpd", "gls", "hermes"]
__version__ = "0.1.0a15"

from . import *

DHL = dhl
DPD = dpd
GLS = gls
Hermes = hermes
PostAT = at_post

def from_barcode(barcode):
    for cls in [dhl.Parcel, dpd.Parcel, gls.Parcel, hermes.Parcel, at_post.Parcel]:
        instanz = cls.from_barcode(barcode)
        if instanz:
            return instanz
