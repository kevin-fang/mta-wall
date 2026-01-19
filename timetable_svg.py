#!/usr/bin/env python3

import datetime as dt
from collections import defaultdict
from typing import Dict, Iterable, List, Tuple
from zoneinfo import ZoneInfo

import requests
from google.transit import gtfs_realtime_pb2

ACE_URL = "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-ace"
NQRW_URL = "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-nqrw"
BDFM_URL = "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-bdfm"
NUMBERTRAINS_URL = "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs"

FEED_URLS = [ACE_URL, NQRW_URL, BDFM_URL, NUMBERTRAINS_URL]
ET_TZ = ZoneInfo("America/New_York")

# Stop IDs without direction suffix.
MY_STOPS = {
    "G21": "Queens Plaza",
    "718": "Queensboro Plaza",
    "R09": "Queensboro Plaza",
}

ROUTE_COLORS = {
    "A": "#0039A6",
    "C": "#0039A6",
    "E": "#0039A6",
    "B": "#FF6319",
    "D": "#FF6319",
    "F": "#FF6319",
    "M": "#FF6319",
    "N": "#FCCC0A",
    "Q": "#FCCC0A",
    "R": "#FCCC0A",
    "W": "#FCCC0A",
    "1": "#EE352E",
    "2": "#EE352E",
    "3": "#EE352E",
    "4": "#00933C",
    "5": "#00933C",
    "6": "#00933C",
    "7": "#B933AD",
    "G": "#6CBE45",
    "J": "#996633",
    "Z": "#996633",
    "L": "#A7A9AC",
    "S": "#808183",
}


def fetch_feed(url: str) -> gtfs_realtime_pb2.FeedMessage:
    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    feed = gtfs_realtime_pb2.FeedMessage()
    feed.ParseFromString(resp.content)
    return feed


def iter_arrivals(
    feed: gtfs_realtime_pb2.FeedMessage,
    stop_map: Dict[str, str],
) -> Iterable[Dict[str, object]]:
    for ent in feed.entity:
        if not ent.HasField("trip_update"):
            continue
        tu = ent.trip_update
        route = tu.trip.route_id
        for stu in tu.stop_time_update:
            stop_id = stu.stop_id
            if not stop_id:
                continue
            stop_key = stop_id[:-1]
            if stop_key not in stop_map:
                continue
            arr = stu.arrival.time if stu.HasField("arrival") else None
            dep = stu.departure.time if stu.HasField("departure") else None
            ts = arr or dep
            if not ts:
                continue
            direction_flag = stop_id[-1]
            direction = "Uptown" if direction_flag == "N" else "Downtown"
            yield {
                "route": route,
                "stop_name": stop_map[stop_key],
                "direction": direction,
                "arrival_time": dt.datetime.fromtimestamp(ts, ET_TZ),
            }


def build_schedule(
    feeds: Iterable[gtfs_realtime_pb2.FeedMessage],
    stop_map: Dict[str, str],
    now: dt.datetime,
    limit: int | None = 2,
) -> List[Dict[str, object]]:
    grouped: Dict[Tuple[str, str, str], List[dt.datetime]] = defaultdict(list)
    for feed in feeds:
        for arrival in iter_arrivals(feed, stop_map):
            arr_time = arrival["arrival_time"]
            if not isinstance(arr_time, dt.datetime) or arr_time <= now:
                continue
            key = (arrival["route"], arrival["stop_name"], arrival["direction"])
            grouped[key].append(arr_time)

    rows = []
    for (route, stop_name, direction), times in grouped.items():
        times.sort()
        next_times = times if limit is None else times[:limit]
        rows.append(
            {
                "route": route,
                "stop_name": stop_name,
                "direction": direction,
                "times": next_times,
            }
        )
    rows.sort(key=lambda r: (r["stop_name"], r["route"], r["direction"]))
    return rows


def render_svg(rows: List[Dict[str, object]], now: dt.datetime) -> str:
    width = 1872
    height = 1404
    margin = 88
    header_h = 132
    table_y = margin + header_h
    table_h = height - margin - table_y
    row_count = max(len(rows), 1)
    row_h = min(78, int(table_h / row_count))
    col_line = margin + 150
    col_stop = col_line + 460
    col_dir = col_stop + 470
    col_next = col_dir + 300

    def esc(text: str) -> str:
        return (
            text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
        )

    def fmt_time(t: dt.datetime) -> str:
        minutes = max(0, int((t - now).total_seconds() // 60))
        return f"{t.strftime('%H:%M')} · {minutes}m"

    bg = "#FAFAF7"
    fg = "#151515"
    header = "#111111"
    muted = "#6F6F6F"
    font = "Avenir Next, Avenir, Helvetica Neue, Helvetica, Arial, sans-serif"

    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="100%" height="100%" viewBox="0 0 {width} {height}" preserveAspectRatio="xMidYMid meet">',
        f'<rect width="{width}" height="{height}" fill="{bg}"/>',
        f'<text x="{margin}" y="{margin + 42}" fill="{header}" font-family="{font}" font-size="58" font-weight="600" letter-spacing="1">MTA ARRIVALS</text>',
        f'<text x="{width - margin}" y="{margin + 42}" fill="{muted}" font-family="{font}" font-size="20" text-anchor="end">As of {now.strftime("%a %b %d %H:%M")} ET</text>',
    ]

    for i, row in enumerate(rows):
        y = table_y + (i + 1) * row_h
        route = str(row["route"])
        stop_name = str(row["stop_name"])
        direction = str(row["direction"])
        times = row["times"]
        t1 = fmt_time(times[0]) if len(times) > 0 else "--:--"
        t2 = fmt_time(times[1]) if len(times) > 1 else "--:--"
        badge_color = ROUTE_COLORS.get(route, "#222222")

        lines.append(
            f'<circle cx="{margin + 30}" cy="{y - row_h / 2}" r="30" fill="{badge_color}"/>'
        )
        lines.append(
            f'<text x="{margin + 30}" y="{y - row_h / 2 + 10}" fill="#FFFFFF" font-family="{font}" font-size="30" font-weight="700" text-anchor="middle">{esc(route)}</text>'
        )
        lines.append(
            f'<text x="{col_line}" y="{y - row_h / 2 + 6}" fill="{fg}" font-family="{font}" font-size="28">{esc(stop_name)}</text>'
        )
        lines.append(
            f'<text x="{col_stop}" y="{y - row_h / 2 + 6}" fill="{muted}" font-family="{font}" font-size="20">{esc(direction)}</text>'
        )
        lines.append(
            f'<text x="{col_dir}" y="{y - row_h / 2 + 6}" fill="{fg}" font-family="{font}" font-size="30" font-weight="600">{t1}</text>'
        )
        lines.append(
            f'<text x="{col_next}" y="{y - row_h / 2 + 6}" fill="{fg}" font-family="{font}" font-size="30" font-weight="600">{t2}</text>'
        )

    lines.append("</svg>")
    return "\n".join(lines)


def generate_svg(
    out_path: str = "timetable.svg",
    stop_map: Dict[str, str] | None = None,
) -> str:
    svg = generate_svg_string(stop_map=stop_map)
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write(svg)
    return out_path


def get_schedule(
    stop_map: Dict[str, str] | None = None,
    limit: int | None = None,
) -> Tuple[List[Dict[str, object]], dt.datetime]:
    stop_map = stop_map or MY_STOPS
    now = dt.datetime.now(ET_TZ)
    feeds = [fetch_feed(url) for url in FEED_URLS]
    rows = build_schedule(feeds, stop_map, now, limit=limit)
    return rows, now


def generate_svg_string(
    stop_map: Dict[str, str] | None = None,
) -> str:
    rows, now = get_schedule(stop_map=stop_map, limit=2)
    return render_svg(rows, now)


if __name__ == "__main__":
    output = generate_svg()
    print(f"Wrote {output}")
