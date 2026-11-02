from django.urls import path

from . import views

urlpatterns = [
    path("trip/<int:trip_id>/seats/", views.seat_map, name="seat_map"),
    path("trip/<int:trip_id>/hold/", views.hold, name="hold"),
    path("booking/<str:pnr>/passengers/", views.passengers, name="passengers"),
    path("booking/<str:pnr>/pay/", views.pay, name="pay"),
    path("booking/<str:pnr>/ticket/", views.ticket, name="ticket"),
    path("booking/<str:pnr>/ticket.pdf", views.ticket_pdf, name="ticket_pdf"),
    path("booking/<str:pnr>/cancel/", views.cancel, name="cancel"),
    path("my-bookings/", views.my_bookings, name="my_bookings"),
]