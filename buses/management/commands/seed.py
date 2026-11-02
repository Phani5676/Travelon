from datetime import datetime, time, timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from buses.models import Bus, Operator, Route, Trip

User = get_user_model()

# (username, company name)
OPERATORS = [
    ("royaltravels", "Royal Travels"),
    ("cityexpress", "City Express"),
]

# (operator username, bus name, bus type, seats)
BUSES = [
    ("royaltravels", "Royal Volvo", Bus.AC_SEATER, 40),
    ("royaltravels", "Royal Sleeper", Bus.AC_SLEEPER, 32),
    ("cityexpress", "City Express Deluxe", Bus.NONAC_SEATER, 44),
    ("cityexpress", "City Night Rider", Bus.NONAC_SLEEPER, 32),
]

# (from, to)
ROUTES = [
    ("Hyderabad", "Vijayawada"),    # 0
    ("Vijayawada", "Hyderabad"),    # 1
    ("Hyderabad", "Bangalore"),     # 2
    ("Hyderabad", "Chennai"),       # 3
    ("Hyderabad", "Visakhapatnam"), # 4
    ("Bangalore", "Chennai"),       # 5
]

# (bus name, route number, departure hour, minute, hours on the road, price)
SCHEDULE = [
    ("Royal Volvo", 0, 6, 30, 4.5, 600),
    ("Royal Volvo", 1, 17, 0, 4.5, 600),
    ("Royal Volvo", 2, 21, 0, 9.5, 1100),
    ("Royal Sleeper", 2, 22, 0, 9.5, 1300),
    ("Royal Sleeper", 3, 20, 30, 11.5, 1400),
    ("City Express Deluxe", 0, 14, 15, 5.0, 450),
    ("City Express Deluxe", 1, 7, 45, 5.0, 450),
    ("City Express Deluxe", 4, 19, 0, 11.0, 800),
    ("City Night Rider", 0, 23, 30, 5.0, 550),
    ("City Night Rider", 5, 9, 0, 6.0, 500),
]


class Command(BaseCommand):
    help = "Create demo operators, buses, routes and trips for the next 8 days."

    def handle(self, *args, **options):
        # 1. Operators (each one is a user account with a company)
        operators = {}
        for username, company in OPERATORS:
            user, created = User.objects.get_or_create(username=username, defaults={"email": f"{username}@example.com"})
            if created:
                user.set_password("busgo123")
                user.save()
            operator, _ = Operator.objects.get_or_create(user=user, defaults={"company_name": company})
            operators[username] = operator

        # 2. Buses (creating a bus also creates its seats)
        buses = {}
        for username, name, bus_type, seats in BUSES:
            bus, _ = Bus.objects.get_or_create(
                operator=operators[username],
                name=name,
                defaults={"bus_type": bus_type, "total_seats": seats},
            )
            buses[name] = bus

        # 3. Routes
        routes = [Route.objects.get_or_create(source=s, destination=d)[0] for s, d in ROUTES]

        # 4. Trips for today and the next 7 days
        created_trips = 0
        today = timezone.localdate()
        for offset in range(8):
            day = today + timedelta(days=offset)
            for bus_name, route_number, hour, minute, hours, price in SCHEDULE:
                departure = timezone.make_aware(datetime.combine(day, time(hour, minute)))
                if departure <= timezone.now():
                    continue  # skip trips that already left
                arrival = departure + timedelta(hours=hours)
                _, created = Trip.objects.get_or_create(
                    bus=buses[bus_name],
                    departure_time=departure,
                    defaults={"route": routes[route_number], "arrival_time": arrival, "price": price},
                )
                created_trips += int(created)

        self.stdout.write(self.style.SUCCESS(f"Done. {created_trips} new trips created."))
        self.stdout.write("Operator logins: royaltravels / busgo123   and   cityexpress / busgo123")