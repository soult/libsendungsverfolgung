import abc
import collections
import csv
import os.path

__all__ = ["base", "events", "dhl", "dpd", "gls", "hermes"]

from . import *

DHL = dhl
DPD = dpd
GLS = gls
Hermes = hermes

def from_barcode(barcode):
    for cls in [dhl.Parcel, dpd.Parcel, gls.Parcel, hermes.Parcel]:
        instanz = cls.from_barcode(barcode)
        if instanz:
            return instanz
