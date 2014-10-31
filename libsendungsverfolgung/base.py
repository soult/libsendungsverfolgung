class Parcel(object):

    def __init__(self, courier, tracking_number, events=None, product=None, weight=None):
        self.courier = courier
        self.tracking_number = tracking_number
        self.product = product
        self.weight = weight
        self.events = events or []

    def __str__(self):
        return "%s %s: %s" % (self.courier.SHORTNAME, self.product or "parcel", self.tracking_number)

class ParcelEvent(object):
    """
    Generic parcel event

    A generic event in the parcel's life.
    """

    def __init__(self, when):
        self.when = when

    def __lt__(self, other):
        return self.when < other.when

    def __eq__(self, other):
        return self.when == other.when

class DataReceivedEvent(ParcelEvent):
    """
    Data received event

    Special event when electronic shipping data has been received by the
    courier. This usually only means that data for the parcel has been
    received, but the parcel has not reached the courier yet.
    """
    pass

class LocationEvent(ParcelEvent):
    """
    Location-based event


    Event that involves the physical parcel being at a specific location. This
    event is not returned directly, instead various subclasses that provide
    more detail are used.
    """

    def __init__(self, location, *args, **kwargs):
        super(LocationEvent, self).__init__(*args, **kwargs)
        self.location = location

class SortEvent(LocationEvent):
    """
    Parcel sort event
    """
    pass

class PickupEvent(LocationEvent):
    """
    Parcel pickup event

    Parcel has been picked up by the courier at the sender's location.
    """
    pass

class InDeliveryEvent(LocationEvent):
    """
    Parcel in delivery event

    The parcel is out for delivery.
    """
    pass

class DeliveryEvent(LocationEvent):
    """
    Parcel delivery event

    The parcel has successfully been delivered.
    """

    def __init__(self, recipient, *args, **kwargs):
        super(DeliveryEvent, self).__init__(*args, **kwargs)
        self.recipient = recipient

class RecipientNotificationEvent(LocationEvent):
    """
    Recipient notification event

    The recipient has been notified.
    """

    def __init__(self, notification, *args, **kwargs):
        super(RecipientNotificationEvent, self).__init__(*args, **kwargs)
        self.notification = notification

class StoreDropoffEvent(LocationEvent):
    """
    Store drop-off event

    The parcel has been dropped of at a store ("Paketshop").
    """
