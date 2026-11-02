# from django.contrib import admin

# Register your models here.
from django.contrib import admin

from .models import Booking, BookingSeat


class BookingSeatInline(admin.TabularInline):
    model = BookingSeat
    extra = 0


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ("pnr", "user", "trip", "status", "seat_summary", "total_amount", "created_at")
    list_filter = ("status",)
    search_fields = ("pnr", "user__username")
    inlines = [BookingSeatInline]