#!/usr/bin/env python

import json
import sys

import libsendungsverfolgung as lsv

if len(sys.argv) > 2:
    if sys.argv[2] == "d":
        parcel = lsv.DPD.Parcel(sys.argv[1])
    else:
        parcel = lsv.Hermes.Parcel(sys.argv[1])
else:
    parcel = lsv.GLS.Parcel(sys.argv[1])

print(parcel)
try:
    print(parcel.weight)
except NotImplementedError:
    pass
for ev in parcel.events:
    print(ev)
    if isinstance(ev, lsv.events.StoreDropoffEvent):
        try:
            print(ev.location.opening_hours)
        except:
            pass
