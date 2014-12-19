#!/usr/bin/env python

import json
import sys

import libsendungsverfolgung

if __name__ == "__main__":
    parcel = libsendungsverfolgung.gls.GLS.autodetect(sys.argv[1], None, None)
    print(parcel)
    print(parcel.weight)
    for ev in parcel.events:
        print(ev)
        if hasattr(ev, "location"):
            print(json.dumps(ev.location, indent=4, sort_keys=True))
#    print(parcel.references)
