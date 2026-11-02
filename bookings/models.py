# from django.db import models

# Create your models here.
from django.conf import settings
from django.db import models
from django.utils import timezone

from buses.models import Seat, Trip


class Booking(models.Model):
    HELD = "held"
    PAID = "paid"
    CANCELLED = "cancelled"
    EXPIRED = "expired"
    STATUS_CHOICES = [
        (HELD, "Held (waiting for payment)"),
        (PAID, "Paid"),
        (CANCELLED, "Cancelled"),
        (EXPIRED, "Expired"),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="bookings")
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name="bookings")
    pnr = models.CharField(max_length=8, unique=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=HELD)
    seat_summary = models.CharField(max_length=200, blank=True)  # for example "2A, 2B"
    fare = models.DecimalField(max_digits=9, decimal_places=2, default=0)
    service_fee = models.DecimalField(max_digits=7, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=9, decimal_places=2, default=0)
    payment_method = models.CharField(max_length=10, blank=True)
    held_until = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.pnr} ({self.status})"

    @property
    def is_expired(self):
        """True when the 5-minute hold has run out."""
        return self.status == self.HELD and self.held_until is not None and self.held_until <= timezone.now()

    @property
    def seconds_left(self):
        """Seconds remaining on the hold (used for the countdown timer)."""
        if self.status != self.HELD or not self.held_until:
            return 0
        return max(int((self.held_until - timezone.now()).total_seconds()), 0)


class BookingSeat(models.Model):
    """One seat inside a booking.

    The unique rule at the bottom means a seat can have only ONE owner on a
    trip. Even if two people click at the same moment, the database refuses
    the second one."""

    GENDER_CHOICES = [("M", "Male"), ("F", "Female"), ("O", "Other")]

    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name="seats")
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name="booked_seats")
    seat = models.ForeignKey(Seat, on_delete=models.CASCADE, related_name="bookings")
    passenger_name = models.CharField(max_length=80, blank=True)
    age = models.PositiveSmallIntegerField(null=True, blank=True)
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, blank=True)

    class Meta:
        ordering = ["seat__row_no", "seat__col_no"]
        constraints = [models.UniqueConstraint(fields=["trip", "seat"], name="unique_seat_per_trip")]

    def __str__(self):
        return f"{self.booking.pnr} - {self.seat.label}"