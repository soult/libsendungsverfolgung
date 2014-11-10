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
#        print("    - %s" % ev)
    #print(json.dumps(parcel, indent=4, sort_keys=True))
