import random
from datetime import timedelta
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from buses.models import Seat, Trip

from .models import Booking, BookingSeat

HOLD_MINUTES = 5                       # how long seats are held
MAX_SEATS_PER_BOOKING = 6              # most seats in one booking
SERVICE_FEE = Decimal("20.00")         # fixed fee added to every booking
PNR_CHARS = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"   # no 0, O, 1, I (easy to confuse)


class SeatError(Exception):
    """Raised when a booking rule is broken. The message is safe to show to the user."""


def generate_pnr():
    """Make a random 6-character ticket code that no other booking uses."""
    while True:
        pnr = "".join(random.choices(PNR_CHARS, k=6))
        if not Booking.objects.filter(pnr=pnr).exists():
            return pnr


def release_expired(trip=None):
    """Free the seats of every hold whose 5 minutes ran out."""
    holds = Booking.objects.filter(status=Booking.HELD, held_until__lte=timezone.now())
    if trip is not None:
        holds = holds.filter(trip=trip)
    ids = list(holds.values_list("id", flat=True))
    if ids:
        BookingSeat.objects.filter(booking_id__in=ids).delete()
        Booking.objects.filter(id__in=ids).update(status=Booking.EXPIRED)


@transaction.atomic
def hold_seats(user, trip_id, seat_ids):
    """Hold the chosen seats for 5 minutes. Returns the new Booking."""

    # THE LOCK: while we work on this trip, nobody else can change it.
    trip = Trip.objects.select_for_update().get(pk=trip_id)

    if trip.departure_time <= timezone.now():
        raise SeatError("This bus has already left.")

    seat_ids = list(dict.fromkeys(seat_ids))  # remove duplicates, keep the order
    if not seat_ids:
        raise SeatError("Select at least one seat.")
    if len(seat_ids) > MAX_SEATS_PER_BOOKING:
        raise SeatError(f"You can book up to {MAX_SEATS_PER_BOOKING} seats at a time.")

    # Free any holds that have run out of time
    release_expired(trip)

    # If this user already holds seats on this trip, drop that old hold (they are choosing again)
    old_holds = list(Booking.objects.filter(user=user, trip=trip, status=Booking.HELD).values_list("id", flat=True))
    if old_holds:
        BookingSeat.objects.filter(booking_id__in=old_holds).delete()
        Booking.objects.filter(id__in=old_holds).update(status=Booking.EXPIRED)

    # Make sure all chosen seats really belong to this bus
    seats = list(Seat.objects.filter(bus=trip.bus, id__in=seat_ids))
    if len(seats) != len(seat_ids):
        raise SeatError("One of the seats is not part of this bus.")

    # Is any chosen seat already taken?
    if BookingSeat.objects.filter(trip=trip, seat__in=seats).exists():
        raise SeatError("Someone just took one of those seats. Pick again.")

    # All good: create the booking and the seats
    fare = trip.price * len(seats)
    booking = Booking.objects.create(
        user=user,
        trip=trip,
        pnr=generate_pnr(),
        status=Booking.HELD,
        seat_summary=", ".join(seat.label for seat in seats),
        fare=fare,
        service_fee=SERVICE_FEE,
        total_amount=fare + SERVICE_FEE,
        held_until=timezone.now() + timedelta(minutes=HOLD_MINUTES),
    )
    BookingSeat.objects.bulk_create(
        [BookingSeat(booking=booking, trip=trip, seat=seat) for seat in seats]
    )
    return booking


@transaction.atomic
def confirm_payment(booking_id, method):
    """Mark a held booking as paid. (The payment itself is only a practice payment.)"""
    booking = Booking.objects.select_for_update().get(pk=booking_id)

    if booking.status == Booking.PAID:
        return booking
    if booking.status != Booking.HELD or booking.is_expired:
        raise SeatError("Your seat hold ended before payment. Pick your seats again.")
    if booking.seats.filter(passenger_name="").exists():
        raise SeatError("Add the passenger details first.")

    booking.status = Booking.PAID
    booking.payment_method = method
    booking.paid_at = timezone.now()
    booking.held_until = None
    booking.save(update_fields=["status", "payment_method", "paid_at", "held_until"])
    return booking


@transaction.atomic
def cancel_booking(booking_id):
    """Cancel a paid booking and free its seats. (The refund is only pretend.)"""
    booking = Booking.objects.select_for_update().select_related("trip").get(pk=booking_id)

    if booking.status != Booking.PAID:
        raise SeatError("Only paid bookings can be cancelled.")
    if booking.trip.departure_time <= timezone.now():
        raise SeatError("This bus has already left, so the booking cannot be cancelled.")

    BookingSeat.objects.filter(booking=booking).delete()
    booking.status = Booking.CANCELLED
    booking.cancelled_at = timezone.now()
    booking.save(update_fields=["status", "cancelled_at"])
    return booking