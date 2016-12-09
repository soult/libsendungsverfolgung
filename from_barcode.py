#!/usr/bin/env python

import libsendungsverfolgung as lsv
import sys

for line in sys.stdin:
    parcel = lsv.from_barcode(line.strip("\r\n"))
    if parcel:
        print(parcel)
        try:
            print(parcel.weight)
        except NotImplementedError:
            pass
        try:
            events = parcel.events
        except BaseException as e:
            print(e)
        else:
            for ev in events:
                print(ev)
                if isinstance(ev, lsv.events.StoreDropoffEvent):
                    try:
                        print(ev.location)
                    except:
                        pass
    else:
        print("unknown")
    print("--------------------------------------------------------")
