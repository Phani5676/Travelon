from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from buses.models import Trip

from .models import Booking, BookingSeat
from .services import (
    HOLD_MINUTES,
    SERVICE_FEE,
    SeatError,
    cancel_booking,
    confirm_payment,
    hold_seats,
    release_expired,
)
from .tickets import qr_data_uri, ticket_pdf_bytes


def get_user_booking(request, pnr):
    """Find a booking by its ticket code. Only its owner may open it."""
    return get_object_or_404(
        Booking.objects.select_related("trip", "trip__route", "trip__bus", "trip__bus__operator"),
        pnr=pnr.upper(),
        user=request.user,
    )


def check_active_hold(request, booking):
    """If the 5-minute hold is over, send the user back to the seat map."""
    release_expired(booking.trip)
    booking.refresh_from_db()
    if booking.status != Booking.HELD:
        messages.error(request, "Your seat hold ended. Pick your seats again.")
        return redirect("seat_map", trip_id=booking.trip_id)
    return None


# ------------------------------------------------------------ Seat map
def seat_map(request, trip_id):
    trip = get_object_or_404(Trip.objects.select_related("bus", "bus__operator", "route"), pk=trip_id)

    if trip.departure_time <= timezone.now():
        messages.error(request, "This bus has already left.")
        return redirect("home")

    release_expired(trip)

    owners = {}
    for item in BookingSeat.objects.filter(trip=trip).select_related("booking"):
        owners[item.seat_id] = (item.booking.user_id, item.booking.status)

    my_id = request.user.id if request.user.is_authenticated else None
    rows = {}
    free_count = 0

    for seat in trip.bus.seats.all():
        owner = owners.get(seat.id)
        if owner is None:
            seat.state = "free"
            free_count += 1
        elif owner[0] == my_id and owner[1] == Booking.HELD:
            seat.state = "mine"
        else:
            seat.state = "booked"
        rows.setdefault(seat.row_no, []).append(seat)

    grid = [
        {
            "left": [s for s in rows[number] if s.col_no < 2],
            "right": [s for s in rows[number] if s.col_no >= 2],
        }
        for number in sorted(rows)
    ]

    context = {
        "trip": trip,
        "grid": grid,
        "free_count": free_count,
        "service_fee": SERVICE_FEE,
        "hold_minutes": HOLD_MINUTES,
    }
    return render(request, "bookings/seats.html", context)


@login_required
@require_POST
def hold(request, trip_id):
    trip = get_object_or_404(Trip, pk=trip_id)

    try:
        seat_ids = [int(value) for value in request.POST.getlist("seats")]
    except ValueError:
        seat_ids = []

    try:
        booking = hold_seats(request.user, trip.id, seat_ids)
    except SeatError as error:
        messages.error(request, str(error))
        return redirect("seat_map", trip_id=trip.id)
    except IntegrityError:
        messages.error(request, "Someone just took one of those seats. Pick again.")
        return redirect("seat_map", trip_id=trip.id)

    return redirect("passengers", pnr=booking.pnr)


# ------------------------------------------------------------ Passenger details
@login_required
def passengers(request, pnr):
    booking = get_user_booking(request, pnr)

    guard = check_active_hold(request, booking)
    if guard:
        return guard

    items = list(booking.seats.select_related("seat"))
    rows = []
    all_valid = True

    for item in items:
        if request.method == "POST":
            name = request.POST.get(f"name_{item.id}", "").strip()
            age_text = request.POST.get(f"age_{item.id}", "").strip()
            gender = request.POST.get(f"gender_{item.id}", "")
        else:
            name = item.passenger_name
            age_text = str(item.age) if item.age else ""
            gender = item.gender

        errors = []
        age = None
        if request.method == "POST":
            if not name or len(name) > 80:
                errors.append("Enter the passenger's name.")
            try:
                age = int(age_text)
                if not 1 <= age <= 120:
                    raise ValueError
            except ValueError:
                errors.append("Enter an age between 1 and 120.")
            if gender not in ("M", "F", "O"):
                errors.append("Choose a gender.")

        if errors:
            all_valid = False
        rows.append({"item": item, "name": name, "age": age_text, "gender": gender, "errors": errors, "age_value": age})

    if request.method == "POST" and all_valid:
        for row in rows:
            item = row["item"]
            item.passenger_name = row["name"]
            item.age = row["age_value"]
            item.gender = row["gender"]
            item.save(update_fields=["passenger_name", "age", "gender"])
        return redirect("pay", pnr=booking.pnr)

    return render(request, "bookings/passengers.html", {"booking": booking, "rows": rows})


# ------------------------------------------------------------ Payment (practice payment)
@login_required
def pay(request, pnr):
    booking = get_user_booking(request, pnr)

    # Already paid? Show the ticket.
    if booking.status == Booking.PAID:
        return redirect("ticket", pnr=booking.pnr)

    guard = check_active_hold(request, booking)
    if guard:
        return guard

    if booking.seats.filter(passenger_name="").exists():
        messages.error(request, "Add the passenger details first.")
        return redirect("passengers", pnr=booking.pnr)

    if request.method == "POST":
        method = request.POST.get("method", "")
        if method not in ("upi", "card"):
            messages.error(request, "Choose UPI or card to pay.")
        else:
            try:
                confirm_payment(booking.id, method)
            except SeatError as error:
                messages.error(request, str(error))
                return redirect("seat_map", trip_id=booking.trip_id)

            messages.success(request, "Payment received. Your ticket is ready.")
            return redirect("ticket", pnr=booking.pnr)

    return render(
        request,
        "bookings/pay.html",
        {"booking": booking, "seat_items": booking.seats.select_related("seat")},
    )


# ------------------------------------------------------------ Ticket
@login_required
def ticket(request, pnr):
    booking = get_user_booking(request, pnr)
    if booking.status != Booking.PAID:
        messages.error(request, "This booking has no valid ticket.")
        return redirect("home")

    return render(
        request,
        "bookings/ticket.html",
        {
            "booking": booking,
            "seat_items": booking.seats.select_related("seat"),
            "qr": qr_data_uri(f"BUSGO|{booking.pnr}"),
        },
    )


@login_required
def ticket_pdf(request, pnr):
    booking = get_user_booking(request, pnr)
    if booking.status != Booking.PAID:
        messages.error(request, "This booking has no valid ticket.")
        return redirect("home")

    response = HttpResponse(ticket_pdf_bytes(booking), content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="busgo-ticket-{booking.pnr}.pdf"'
    return response



# ------------------------------------------------------------ My bookings
@login_required
def my_bookings(request):
    release_expired()

    bookings = (
        Booking.objects.filter(user=request.user)
        .exclude(status=Booking.EXPIRED)
        .select_related("trip", "trip__route", "trip__bus", "trip__bus__operator")
    )

    now = timezone.now()
    upcoming, past, cancelled, pending = [], [], [], []
    for booking in bookings:
        if booking.status == Booking.CANCELLED:
            cancelled.append(booking)
        elif booking.status == Booking.HELD:
            pending.append(booking)
        elif booking.trip.departure_time > now:
            upcoming.append(booking)
        else:
            past.append(booking)

    upcoming.sort(key=lambda b: b.trip.departure_time)

    return render(
        request,
        "bookings/my_bookings.html",
        {"upcoming": upcoming, "past": past, "cancelled": cancelled, "pending": pending},
    )


@login_required
@require_POST
def cancel(request, pnr):
    booking = get_user_booking(request, pnr)
    try:
        cancel_booking(booking.id)
        messages.success(request, f"Booking {booking.pnr} cancelled. Your refund is on its way (pretend).")
    except SeatError as error:
        messages.error(request, str(error))
    return redirect("my_bookings")