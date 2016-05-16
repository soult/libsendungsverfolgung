import abc
import collections
import csv
import os.path

__all__ = ["base", "events", "dpd", "gls", "hermes"]

from . import *

DPD = dpd
GLS = gls
Hermes = hermes

def autodetect(tracking_number):
    for cls in [gls.Parcel]:
        try:
            return cls.__init__(tracking_number)
        except ValueError:
            pass
