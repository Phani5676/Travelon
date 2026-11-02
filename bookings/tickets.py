"""Makes the QR code and the PDF ticket."""
import base64
import io

import qrcode
from django.utils import timezone
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas


def qr_png_bytes(text):
    image = qrcode.make(text)
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def qr_data_uri(text):
    """The QR image as text, so an HTML page can show it without a separate file."""
    return "data:image/png;base64," + base64.b64encode(qr_png_bytes(text)).decode()


def ticket_pdf_bytes(booking):
    trip = booking.trip
    seats = list(booking.seats.select_related("seat"))
    depart = timezone.localtime(trip.departure_time)
    arrive = timezone.localtime(trip.arrival_time)

    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    left = 20 * mm

    # Green header band
    pdf.setFillColorRGB(0.09, 0.53, 0.33)
    pdf.rect(0, height - 38 * mm, width, 38 * mm, fill=1, stroke=0)
    pdf.setFillColorRGB(1, 1, 1)
    pdf.setFont("Helvetica-Bold", 24)
    pdf.drawString(left, height - 22 * mm, "BusGo")
    pdf.setFont("Helvetica", 11)
    pdf.drawString(left, height - 30 * mm, "E-ticket  |  Show this at boarding")

    # Route title
    y = height - 55 * mm
    pdf.setFillColorRGB(0.1, 0.1, 0.1)
    pdf.setFont("Helvetica-Bold", 20)
    pdf.drawString(left, y, f"{trip.route.source}  to  {trip.route.destination}")

    def line(label, value, y_pos):
        pdf.setFont("Helvetica", 10)
        pdf.setFillColorRGB(0.4, 0.4, 0.4)
        pdf.drawString(left, y_pos, label)
        pdf.setFont("Helvetica-Bold", 12)
        pdf.setFillColorRGB(0.1, 0.1, 0.1)
        pdf.drawString(left + 38 * mm, y_pos, value)

    y -= 14 * mm
    line("PNR", booking.pnr, y)
    y -= 8 * mm
    line("Operator", trip.bus.operator.company_name, y)
    y -= 8 * mm
    line("Bus", f"{trip.bus.name} ({trip.bus.get_bus_type_display()})", y)
    y -= 8 * mm
    line("Departs", depart.strftime("%d %b %Y, %H:%M"), y)
    y -= 8 * mm
    line("Arrives", arrive.strftime("%d %b %Y, %H:%M"), y)
    y -= 8 * mm
    line("Seats", booking.seat_summary, y)
    y -= 8 * mm
    line("Paid", f"Rs. {booking.total_amount}", y)

    # Passenger list
    y -= 14 * mm
    pdf.setFont("Helvetica-Bold", 13)
    pdf.drawString(left, y, "Passengers")
    pdf.setFont("Helvetica", 11)
    for item in seats:
        y -= 7 * mm
        gender = item.get_gender_display() if item.gender else ""
        pdf.drawString(left, y, f"Seat {item.seat.label}:  {item.passenger_name}, {item.age} yrs, {gender}")

    # QR code at the top right
    qr = ImageReader(io.BytesIO(qr_png_bytes(f"BUSGO|{booking.pnr}")))
    pdf.drawImage(qr, width - 70 * mm, height - 100 * mm, 45 * mm, 45 * mm)
    pdf.setFont("Helvetica", 8)
    pdf.setFillColorRGB(0.4, 0.4, 0.4)
    pdf.drawString(width - 70 * mm, height - 104 * mm, "Scan to verify")

    pdf.showPage()
    pdf.save()
    return buffer.getvalue()