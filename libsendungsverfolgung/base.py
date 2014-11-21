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

    def __str__(self):
        if hasattr(self, "DESCRIPTION"):
            return "%s: %s" % (self.when, self.DESCRIPTION)
        else:
            return str(self.when)

class DataReceivedEvent(ParcelEvent):
    """
    Data received event

    Special event when electronic shipping data has been received by the
    courier. This usually only means that data for the parcel has been
    received, but the parcel has not reached the courier yet.
    """

    DESCRIPTION = "received electronic shipping information"

class CancelledEvent(ParcelEvent):
    """
    Parcel cancelled event

    The electronic shipping information which has previously been avisoed has
    been cancelled. The parcel will not be sent.
    """

    DESCRIPTION = "cancelled"

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

    def __str__(self):
        if hasattr(self, "DESCRIPTION"):
            return "%s %s: %s" % (self.when, self.location, self.DESCRIPTION)
        else:
            return "%s %s" % (self.when, self.location)

class SortEvent(LocationEvent):
    """
    Parcel sort event
    """

    DESCRIPTION = "sort"

class StoredEvent(LocationEvent):
    """
    Parcel stored event

    Parcel has been stored. This can be due to errors (e.g. address not found)
    but it can also just be a routine step (e.g. a parcel being stored until
    the next truck to another depot is ready.
    """

    DESCRIPTION = "stored"

class PickupEvent(LocationEvent):
    """
    Parcel pickup event

    Parcel has been picked up by the courier at the sender's location.
    """

    DESCRIPTION = "pickup at sender's location"

class InDeliveryEvent(LocationEvent):
    """
    Parcel in delivery event

    The parcel is out for delivery.
    """

    DESCRIPTION = "out for delivery"

class DeliveryEvent(LocationEvent):
    """
    Parcel delivery event

    The parcel has successfully been delivered.
    """

    DESCRIPTION = "delivered"

    def __init__(self, recipient, *args, **kwargs):
        super(DeliveryEvent, self).__init__(*args, **kwargs)
        self.recipient = recipient

class DeliveryNeighbourEvent(DeliveryEvent):
    """
    Parcel neighbour delivery event

    The parcel has been delivered to a neighbour.
    """
    DESCRIPTION = "delivered to neighbour"

class FailedDeliveryEvent(LocationEvent):
    """
    Parcel delivery failed event

    The parcel could not be delivered.
    """
    DESCRIPTION = "delivery failed"

class RecipientUnavailableEvent(FailedDeliveryEvent):
    """
    Recipient unavailable event

    The parcel could not be delivered because the recipient was not available.
    """
    DESCRIPTION = "delivery failed because recipient unavailable"

class WrongAddressEvent(FailedDeliveryEvent):
    """
    Wrong address event

    The parcel could not be delivered due to a wrong address.
    """

    DESCRIPTION = "delivery failed due to wrong address"

class DeliveryRefusedEvent(FailedDeliveryEvent):
    """
    Delivery refused event

    The parcel could not be delivered because the recipient refused to accept it
    """

    DESCRIPTION = "delivery refused by recipient"

class RecipientNotificationEvent(LocationEvent):
    """
    Recipient notification event

    The recipient has been notified.
    """

    DESCRIPTION = "recipient notified"

    def __init__(self, notification, *args, **kwargs):
        super(RecipientNotificationEvent, self).__init__(*args, **kwargs)
        self.notification = notification

class StoreDropoffEvent(LocationEvent):
    """
    Store drop-off event

    The parcel has been dropped of at a store ("Paketshop").
    """

    DESCRIPTION = "dropped of at store"

class StoreNotPickedUpEvent(FailedDeliveryEvent):
    """
    Store not picked up event

    The parcel was dropped off at a store but never picked up by the recipient
    """

    DESCRIPTION = "storage time exceeded"

class ReturnEvent(LocationEvent):
    """
    Parcel return event

    The parcel will be returned to the sender
    """

    DESCRIPTION = "returning"
