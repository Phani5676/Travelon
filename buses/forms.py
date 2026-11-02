from django import forms

from .models import Bus, Route, Trip


class BootstrapMixin:
    """Gives every form box the Bootstrap look."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            widget = field.widget
            if isinstance(widget, forms.CheckboxInput):
                widget.attrs["class"] = "form-check-input"
            elif isinstance(widget, forms.Select):
                widget.attrs["class"] = "form-select"
            else:
                widget.attrs["class"] = "form-control"


class BusForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = Bus
        fields = ["name", "bus_type", "total_seats"]
        help_texts = {"total_seats": "Between 8 and 60. Seats are laid out two on each side of the aisle."}


class RouteForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = Route
        fields = ["source", "destination"]

    def clean(self):
        data = super().clean()
        source = (data.get("source") or "").strip().title()
        destination = (data.get("destination") or "").strip().title()
        if source and destination and source == destination:
            raise forms.ValidationError("From and To must be different cities.")
        data["source"], data["destination"] = source, destination
        return data


class TripForm(BootstrapMixin, forms.ModelForm):
    DT_FORMAT = "%Y-%m-%dT%H:%M"

    departure_time = forms.DateTimeField(
        input_formats=[DT_FORMAT],
        widget=forms.DateTimeInput(attrs={"type": "datetime-local"}, format=DT_FORMAT),
    )
    arrival_time = forms.DateTimeField(
        input_formats=[DT_FORMAT],
        widget=forms.DateTimeInput(attrs={"type": "datetime-local"}, format=DT_FORMAT),
    )

    class Meta:
        model = Trip
        fields = ["bus", "route", "departure_time", "arrival_time", "price"]

    def __init__(self, *args, operator=None, **kwargs):
        super().__init__(*args, **kwargs)
        # An operator may only schedule trips for their own buses
        if operator is not None:
            self.fields["bus"].queryset = Bus.objects.filter(operator=operator)

    def clean(self):
        data = super().clean()
        departure, arrival, price = data.get("departure_time"), data.get("arrival_time"), data.get("price")
        if departure and arrival and arrival <= departure:
            self.add_error("arrival_time", "Arrival must be after departure.")
        if price is not None and price <= 0:
            self.add_error("price", "Price must be more than zero.")
        return data