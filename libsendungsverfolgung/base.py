import abc
import collections
import csv
import os.path

def load_countries():
    filename = os.path.join(os.path.dirname(__file__), "country-codes.csv")
    if not os.path.exists(filename):
        return []

    country = collections.namedtuple("Country", ["name", "alpha2", "alpha3", "numeric"])
    countries = []
    with open(filename, "r", encoding="utf-8") as fileobj:
        reader = csv.DictReader(fileobj)
        for row in reader:
            countries.append(country(
                row["name"],
                row["ISO3166-1-Alpha-2"],
                row["ISO3166-1-Alpha-3"],
                row["ISO3166-1-numeric"]
            ))
    return countries

countries = load_countries()

class Location(object):

    def __init__(self, *args, **kwargs):
        for k in ["name", "address", "postcode", "city"]:
            self.__dict__[k] = kwargs.get(k)

        if "country" in kwargs:
            self.__dict__["country"] = self._find_country("name", kwargs["country"])
        elif "country_code" in kwargs:
            cc = kwargs["country_code"]
            if len(cc) == 2:
                self.__dict__["country"] = self._find_country("alpha2", cc)
            elif len(cc) == 3:
                self.__dict__["country"] = self._find_country("alpha3", cc)
            else:
                raise ValueError("Unexpected length %i for country_code" % len(cc))
        elif "country_numeric" in kwargs:
            self.__dict__["country"] = self._find_country("numeric", kwargs["country_numeric"])

    @staticmethod
    def _find_country(field_name, value):
        value = value.lower()
        for country in countries:
            if getattr(country, field_name).lower() == value:
                return country

    def __str__(self):
        if self.city:
            return "%s, %s" % (self.city, self.country.alpha2)
        else:
            return self.country.alpha2

class Store(Location):

    def __init__(self, *args, **kwargs):
        super(Store, self).__init__(*args, **kwargs)
        for k in ["opening_hours", "phone", "fax", "email"]:
            self.__dict__[k] = kwargs.get(k)

class Parcel(metaclass=abc.ABCMeta):

    @abc.abstractproperty
    def tracking_number(self):
        pass

    @property
    def product(self):
        raise NotImplementedError()

    @property
    def weight(self):
        raise NotImplementedError()

    @property
    def recipient(self):
        raise NotImplementedError()

    def __str__(self):
        try:
            product = self.product
        except NotImplementedError:
            product = "Parcel"
        return "<%s %s>" % (product, self.tracking_number)
