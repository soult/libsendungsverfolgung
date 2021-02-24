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

class RedirectEvent(ParcelEvent):
    """
    Redirect event

    The courier has been instructed to send the parcel to a different address.
    """

    DESCRIPTION = "redirected"

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
        if self.location == None:
            return super(LocationEvent, self).__str__()
        if hasattr(self, "DESCRIPTION"):
            return "%s, %s: %s" % (self.when, self.location, self.DESCRIPTION)
        else:
            return "%s, %s" % (self.when, self.location)

    def __eq__(self, other):
        return self.when == other.when and self.location == other.location

class ParcelLabelPrintedEvent(LocationEvent):
    """
    Parcel label has been printed

    The parcel label, usually for a pickup order, has been printed.
    """

    DESCRIPTION = "parcel label printed"

class SortEvent(LocationEvent):
    """
    Parcel sort event
    """

    DESCRIPTION = "sort"

class ManualSortEvent(SortEvent):
    """
    Parcel manual sort event"
    """

    DESCRIPTION = "sort (manual)"

class InboundSortEvent(SortEvent):
    """
    Inbound parcel sort event
    """

    DESCRIPTION = "inbound sort"

class OutboundSortEvent(SortEvent):
    """
    Outbound parcel sort event
    """

    DESCRIPTION = "outbound sort"

class StoredEvent(LocationEvent):
    """
    Parcel stored event

    Parcel has been stored. This can be due to errors (e.g. address not found)
    but it can also just be a routine step (e.g. a parcel being stored until
    the next truck to another depot is ready.
    """

    DESCRIPTION = "stored"

class PostedEvent(LocationEvent):
    """
    Parcel posted event

    Parcel has been posted at the Parcel shop ("Paketshop") or postal office by
    the sender.
    """

    DESCRIPTION = "posted by sender"

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

    def __str__(self):
        if self.recipient:
            return "%s, %s: %s (signature: %s)" % (self.when, self.location, self.DESCRIPTION, self.recipient)
        else:
            return "%s, %s: %s" % (self.when, self.location, self.DESCRIPTION)

class DeliveryDropOffEvent(LocationEvent):
    """
    Parcel drop off delivery event

    The parcel has been dropped of by the courier without getting a signature,
    usually because it was requested by the client ("Abstellgenehmigung").
    """

    DESCRIPTION = "delivered without signature"

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

    The parcel has been dropped off at a store ("Paketshop").
    """

    DESCRIPTION = "dropped off at store"

class StorePickupEvent(LocationEvent):
    """
    Store pick-up event

    The parcel has been picked from a store ("Paketshop").
    """

    DESCRIPTION = "picked up from store"

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
