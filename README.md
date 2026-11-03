https://travelon-7zhl.onrender.com

# BusGo: Bus Ticket Booking (Django + PostgreSQL)

A bus booking web app in the style of redBus. Passengers search buses, pick exact seats on a seat map, pay (simulated) and get a QR-code ticket. Bus operators manage their own buses, routes and trips.

**Live demo:** YOUR-LINK (free hosting: the first load can take about a minute)

## Features
- Search buses by route and date
- Seat map with free, yours and taken seats
- Seat locking: chosen seats are held for 5 minutes with a countdown, so two people cannot book the same seat
- Passenger details, simulated payment, QR-code ticket and PDF download
- Share the ticket by WhatsApp or email
- My Bookings with cancel (seats become free again)
- Operator dashboard: add buses, routes and trips, and see bookings per trip

## Demo logins
Operators: `royaltravels` / `busgo123` and `cityexpress` / `busgo123`. Passengers can sign up.

## Tech stack
Python, Django, PostgreSQL, Bootstrap 5, JavaScript, ReportLab, qrcode, Gunicorn, WhiteNoise, Render

## How seat locking works
- Holding seats runs inside a database transaction.
- The trip row is locked with `select_for_update()`, so simultaneous clicks are handled one after the other.
- A unique constraint on (trip, seat) means the database itself refuses a second owner for a seat.
- A hold lasts 5 minutes. Expired holds are released automatically.

## Run it locally
1. Install Python and PostgreSQL, then create a database named `busgo`.
2. Create a virtual environment and run `pip install -r requirements.txt`.
3. Create a `.env` file with `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST` and `DB_PORT`.
4. Run:
```
python manage.py migrate
python manage.py createsuperuser
python manage.py seed
python manage.py runserver
```

## Next ideas
Real payment gateway, automatic email and WhatsApp tickets, ratings, live bus tracking.