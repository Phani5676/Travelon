# from django.db import models

# Create your models here.
from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class Operator(models.Model):
    """A bus company. Linked to one user account."""

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="operator")
    company_name = models.CharField(max_length=100)

    def __str__(self):
        return self.company_name


class Bus(models.Model):
    AC_SEATER = "AC_SEATER"
    NONAC_SEATER = "NONAC_SEATER"
    AC_SLEEPER = "AC_SLEEPER"
    NONAC_SLEEPER = "NONAC_SLEEPER"
    BUS_TYPES = [
        (AC_SEATER, "AC Seater"),
        (NONAC_SEATER, "Non-AC Seater"),
        (AC_SLEEPER, "AC Sleeper"),
        (NONAC_SLEEPER, "Non-AC Sleeper"),
    ]

    operator = models.ForeignKey(Operator, on_delete=models.CASCADE, related_name="buses")
    name = models.CharField(max_length=100)
    bus_type = models.CharField(max_length=20, choices=BUS_TYPES, default=AC_SEATER)
    total_seats = models.PositiveSmallIntegerField(
        default=40, validators=[MinValueValidator(8), MaxValueValidator(60)]
    )

    class Meta:
        verbose_name_plural = "buses"

    def __str__(self):
        return f"{self.name} ({self.get_bus_type_display()})"

    def save(self, *args, **kwargs):
        creating = self.pk is None
        super().save(*args, **kwargs)
        if creating:
            self.create_seats()

    def create_seats(self):
        """Make the seats automatically: 1A 1B | 1C 1D, then 2A 2B | 2C 2D, and so on."""
        letters = "ABCD"
        seats = []
        count = 0
        row = 1
        while count < self.total_seats:
            for col in range(4):
                if count >= self.total_seats:
                    break
                seats.append(Seat(bus=self, label=f"{row}{letters[col]}", row_no=row, col_no=col))
                count += 1
            row += 1
        Seat.objects.bulk_create(seats)


class Seat(models.Model):
    bus = models.ForeignKey(Bus, on_delete=models.CASCADE, related_name="seats")
    label = models.CharField(max_length=5)
    row_no = models.PositiveSmallIntegerField()
    col_no = models.PositiveSmallIntegerField()  # 0 and 1 = left side, 2 and 3 = right side

    class Meta:
        ordering = ["row_no", "col_no"]
        constraints = [models.UniqueConstraint(fields=["bus", "label"], name="unique_seat_label_per_bus")]

    def __str__(self):
        return f"{self.bus.name} - {self.label}"


class Route(models.Model):
    source = models.CharField(max_length=60)
    destination = models.CharField(max_length=60)

    class Meta:
        ordering = ["source", "destination"]
        constraints = [models.UniqueConstraint(fields=["source", "destination"], name="unique_route")]

    def __str__(self):
        return f"{self.source} to {self.destination}"


class Trip(models.Model):
    """One bus running one route at one date and time."""

    bus = models.ForeignKey(Bus, on_delete=models.CASCADE, related_name="trips")
    route = models.ForeignKey(Route, on_delete=models.CASCADE, related_name="trips")
    departure_time = models.DateTimeField()
    arrival_time = models.DateTimeField()
    price = models.DecimalField(max_digits=8, decimal_places=2)

    class Meta:
        ordering = ["departure_time"]
        constraints = [
            models.UniqueConstraint(fields=["bus", "departure_time"], name="one_trip_per_bus_per_time")
        ]

    def __str__(self):
        return f"{self.route} | {self.bus.name} | {self.departure_time:%d %b %H:%M}"

    @property
    def duration(self):
        minutes = int((self.arrival_time - self.departure_time).total_seconds() // 60)
        return f"{minutes // 60}h {minutes % 60:02d}m"