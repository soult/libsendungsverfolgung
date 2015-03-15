#!/usr/bin/env python

import json
import sys

import libsendungsverfolgung as lsv

if len(sys.argv) > 2:
    parcel = lsv.DPD.Parcel(sys.argv[1])
else:
    parcel = lsv.GLS.Parcel(sys.argv[1])

print(parcel)
for ev in parcel.events:
    print(ev)
