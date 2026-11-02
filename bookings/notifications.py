import logging

from django.conf import settings
from django.core.mail import EmailMessage
from django.utils import timezone

from .tickets import ticket_pdf_bytes

logger = logging.getLogger(__name__)


def send_ticket_email(booking):
    """Email the ticket (PDF attached) to the booking's contact email.
    Returns True if it was sent. Never raises, so a mail problem cannot break a booking."""
    if not (settings.GMAIL_USER and settings.GMAIL_APP_PASSWORD):
        return False  # real email is not set up yet, so do nothing
    to_email = booking.contact_email or booking.user.email
    if not to_email:
        return False

    trip = booking.trip
    departs = timezone.localtime(trip.departure_time).strftime("%a, %d %b %Y, %H:%M")

    subject = f"Your BusGo ticket {booking.pnr}: {trip.route.source} to {trip.route.destination}"
    body = (
        f"Hi {booking.user.username},\n\n"
        f"Your bus ticket is confirmed.\n\n"
        f"Booking code: {booking.pnr}\n"
        f"Route: {trip.route.source} to {trip.route.destination}\n"
        f"Bus: {trip.bus.name} ({trip.bus.get_bus_type_display()})\n"
        f"Departs: {departs}\n"
        f"Seats: {booking.seat_summary}\n"
        f"Total paid: Rs. {booking.total_amount}\n\n"
        f"Your ticket is attached as a PDF. Show the QR code when you board.\n\n"
        f"Have a safe trip,\n"
        f"BusGo"
    )

    try:
        message = EmailMessage(subject, body, settings.DEFAULT_FROM_EMAIL, [to_email])
        message.attach(f"busgo-ticket-{booking.pnr}.pdf", ticket_pdf_bytes(booking), "application/pdf")
        message.send()
        return True
    except Exception:
        logger.exception("Could not email ticket %s", booking.pnr)
        return False