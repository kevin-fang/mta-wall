# MTA Wall

Simple MTA arrival display with an SVG timetable and a mobile-first HTML view.

## What it does
- Fetches MTA GTFS real-time feeds and groups arrivals by line/stop/direction.
- Renders a 1872x1404 SVG timetable (next 2 trains only).
- Serves a mobile-friendly HTML page with expandable "More trains" lists.
- Supports dark mode and auto-refresh.

## Requirements
- Python 3.10+
- `requests`
- `gtfs-realtime-bindings`

## Setup
Install dependencies:
```bash
pip install requests gtfs-realtime-bindings
```

If your MTA feed access requires an API key:
```bash
export MTA_API_KEY="your_key_here"
```

## Run the server
```bash
python server.py
```

By default it binds to `0.0.0.0:8000`.

Endpoints:
- `/` or `/mobile` - mobile HTML page
- `/timetable.svg` or `/svg` - raw SVG only

## Generate a static SVG
```bash
python timetable_svg.py
```

This writes `timetable.svg` in the project directory.

## Customize stops
Edit `MY_STOPS` in `timetable_svg.py` to change which stops are tracked.

## Notes
- The SVG is limited to the next 2 trains per line/stop/direction.
- The HTML view shows all future trains with a dropdown per card.
