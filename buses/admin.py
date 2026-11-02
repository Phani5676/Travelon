# from django.contrib import admin

# Register your models here.
from django.contrib import admin

from .models import Bus, Operator, Route, Seat, Trip


@admin.register(Operator)
class OperatorAdmin(admin.ModelAdmin):
    list_display = ("company_name", "user")


@admin.register(Bus)
class BusAdmin(admin.ModelAdmin):
    list_display = ("name", "operator", "bus_type", "total_seats")
    list_filter = ("bus_type", "operator")


@admin.register(Route)
class RouteAdmin(admin.ModelAdmin):
    list_display = ("source", "destination")
    search_fields = ("source", "destination")


@admin.register(Trip)
class TripAdmin(admin.ModelAdmin):
    list_display = ("route", "bus", "departure_time", "arrival_time", "price")
    list_filter = ("route", "bus__operator")


@admin.register(Seat)
class SeatAdmin(admin.ModelAdmin):
    list_display = ("bus", "label", "row_no", "col_no")
    list_filter = ("bus",)