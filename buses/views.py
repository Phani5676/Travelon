from datetime import datetime, timedelta
from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from bookings.models import Booking
from bookings.services import release_expired

from .forms import BusForm, RouteForm, TripForm
from .models import Route, Trip


def operator_required(view):
    """Only logged-in users that have a bus company may open the page."""

    @login_required
    @wraps(view)
    def wrapper(request, *args, **kwargs):
        if not hasattr(request.user, "operator"):
            messages.error(request, "That page is for bus operators. Sign up as an operator to use it.")
            return redirect("home")
        return view(request, *args, **kwargs)

    return wrapper


# ------------------------------------------------------------ Passenger side
def home(request):
    cities = sorted({city for pair in Route.objects.values_list("source", "destination") for city in pair})
    today = timezone.localdate().isoformat()
    return render(request, "buses/home.html", {"cities": cities, "today": today})


def search_results(request):
    source = request.GET.get("from", "").strip()
    destination = request.GET.get("to", "").strip()
    date_text = request.GET.get("date", "").strip()

    try:
        day = datetime.strptime(date_text, "%Y-%m-%d").date()
    except ValueError:
        messages.error(request, "Pick a travel date to search.")
        return redirect("home")

    if not source or not destination:
        messages.error(request, "Enter both a From city and a To city.")
        return redirect("home")

    start = timezone.make_aware(datetime.combine(day, datetime.min.time()))
    end = start + timedelta(days=1)

    trips = (
        Trip.objects.filter(
            route__source__iexact=source,
            route__destination__iexact=destination,
            departure_time__gte=start,
            departure_time__lt=end,
            departure_time__gt=timezone.now(),
        )
        .select_related("bus", "bus__operator", "route")
        .order_by("departure_time")
    )

    return render(
        request,
        "buses/results.html",
        {"trips": trips, "source": source, "destination": destination, "day": day},
    )


# ------------------------------------------------------------ Operator side
@operator_required
def operator_dashboard(request):
    operator = request.user.operator
    release_expired()

    trips = (
        Trip.objects.filter(bus__operator=operator, departure_time__gte=timezone.now() - timedelta(hours=6))
        .select_related("bus", "route")
        .annotate(booked=Count("booked_seats"))
        .order_by("departure_time")[:30]
    )
    paid_bookings = Booking.objects.filter(trip__bus__operator=operator, status=Booking.PAID).count()

    context = {
        "operator": operator,
        "trips": trips,
        "buses": operator.buses.all(),
        "paid_bookings": paid_bookings,
    }
    return render(request, "buses/operator_dashboard.html", context)


@operator_required
def add_bus(request):
    form = BusForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        bus = form.save(commit=False)
        bus.operator = request.user.operator
        bus.save()  # saving a bus also creates its seats
        messages.success(request, f"{bus.name} added with {bus.total_seats} seats.")
        return redirect("operator_dashboard")
    return render(request, "buses/form_page.html", {"form": form, "title": "Add a bus", "button": "Save bus"})


@operator_required
def add_route(request):
    form = RouteForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Route added.")
        return redirect("operator_dashboard")
    return render(request, "buses/form_page.html", {"form": form, "title": "Add a route", "button": "Save route"})


@operator_required
def add_trip(request):
    form = TripForm(request.POST or None, operator=request.user.operator)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Trip scheduled. Passengers can book it now.")
        return redirect("operator_dashboard")
    return render(request, "buses/form_page.html", {"form": form, "title": "Schedule a trip", "button": "Save trip"})


@operator_required
def trip_bookings(request, trip_id):
    trip = get_object_or_404(
        Trip.objects.select_related("bus", "route"), pk=trip_id, bus__operator=request.user.operator
    )
    bookings = (
        Booking.objects.filter(trip=trip, status=Booking.PAID)
        .select_related("user")
        .prefetch_related("seats__seat")
    )
    return render(request, "buses/trip_bookings.html", {"trip": trip, "bookings": bookings})