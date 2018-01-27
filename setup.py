#!/usr/bin/env python

from distutils.core import setup

setup(
    name="libsendungsverfolgung",
    version="0.1.0a3",
    description="Python3 library for tracking parcels shipped with various couriers",
    long_description="A Python3 library for tracking parcels and other shipments. It abstracts the various status messages from each shipping company into a simple hierachy of delivery events.",
    author="David Triendl",
    author_email="david@triendl.name",
    packages=["libsendungsverfolgung"],
    package_data={"libsendungsverfolgung": ["country-codes.csv"]},
    install_requires=["requests>=2.0.0"],
)
