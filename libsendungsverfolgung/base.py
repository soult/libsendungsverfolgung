import abc
import collections
import csv
import os.path

TIMEOUT = 10


class LSVException(Exception):
    pass


class UnknownParcelException(Exception):
    pass


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
        else:
            self.__dict__["country"] = None

    @staticmethod
    def _find_country(field_name, value):
        value = value.lower()
        for country in countries:
            if getattr(country, field_name).lower() == value:
                return country

    def __str__(self):
        if self.city:
            if self.country:
                return "%s, %s" % (self.city, self.country.alpha2)
            else:
                return self.city
        elif self.country:
            return self.country.alpha2
        else:
            return "n/a"

    def __eq__(self, other):
        return self.name == other.name and self.address == other.address and \
                self.city == other.city and self.country == other.country

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
    def tracking_link(self):
        raise NotImplementedError()

    @property
    def product(self):
        raise NotImplementedError()

    @property
    def weight(self):
        raise NotImplementedError()

    @property
    def recipient(self):
        raise NotImplementedError()

    @property
    def is_cash_on_delivery(self):
        raise NotImplementedError()

    @property
    def is_courier_pickup(self):
        raise NotImplementedError()

    @property
    def is_parcelshop_return(self):
        raise NotImplementedError()

    @property
    def is_express(self):
        raise NotImplementedError()

    def __str__(self):
        try:
            product = self.product
        except NotImplementedError:
            product = "Parcel"
        return "<%s %s: %s>" % (self.COMPANY_SHORTNAME, product, self.tracking_number)
