from django.urls import path

from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("search/", views.search_results, name="search"),
    path("operator/", views.operator_dashboard, name="operator_dashboard"),
    path("operator/bus/new/", views.add_bus, name="add_bus"),
    path("operator/route/new/", views.add_route, name="add_route"),
    path("operator/trip/new/", views.add_trip, name="add_trip"),
    path("operator/trip/<int:trip_id>/bookings/", views.trip_bookings, name="trip_bookings"),
]