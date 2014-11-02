#!/usr/bin/env python

from bottle import response, request, route, run, view
import json

import libsendungsverfolgung as lsv

@route("/")
@view("index")
def webindex():
    return {}

@route("/gls")
@view("gls")
def webgls():
    return {}

@route("/gls_json_weight")
def webgls_json_weight():
    response.content_type = "application/json"
    data = {}
    barcode = str(request.query.barcode).strip()
    try:
        parcel = lsv.GLS.get_parcel(barcode)
    except:
        data["status"] = "error"
        data["barcode"] = barcode
    else:
        data["status"] = "success"
        data["barcode"] = parcel.tracking_number
        data["weight"] = ("%0.2f" % parcel.weight).replace(".", ",")
        data["date"] = sorted(parcel.events)[0].when.strftime("%d.%m.%Y")
    print(data)
    return json.dumps(data)

run(host='127.0.0.1', port=8000, debug=True)
