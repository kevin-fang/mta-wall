#!/usr/bin/env python

import requests
from google.transit import gtfs_realtime_pb2
import datetime as dt
from collections import defaultdict

SUBWAY_DATA = "https://rrgtfsfeeds.s3.amazonaws.com/gtfs_subway.zip"

ACE_URL = "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-ace"
NQRW_URL = "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-nqrw"
BDFM_URL = "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-bdfm"
NUMBERTRAINS_URL = "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs"

urls = [ACE_URL, NQRW_URL, BDFM_URL, NUMBERTRAINS_URL]


queens_plaza = "G21"
queensboro_plaza = "718"
queensboro_plaza_nw = "R09"

my_stops = {"G21": "Queens Plaza", "718": "Queensboro Plaza", "R09": "Queensboro Plaza"}

# { train: [{ stop, direction, is_uptown, arrival time }] }
train_map = {}

for url in urls:
    # print(f"Querying {url.split('-')[-1]}")
    resp = requests.get(url, timeout=10)
    resp.raise_for_status()

    feed = gtfs_realtime_pb2.FeedMessage()
    feed.ParseFromString(resp.content)

    train_map = defaultdict(list)
    for ent in feed.entity:
        if not ent.HasField("trip_update"):
            continue
        tu = ent.trip_update
        trip = tu.trip.trip_id
        route = tu.trip.route_id

        for stu in tu.stop_time_update:
            sid = stu.stop_id
            arr = stu.arrival.time if stu.HasField("arrival") else None
            dep = stu.departure.time if stu.HasField("departure") else None
            if not arr or not dep:
                continue
            arr_time = dt.datetime.fromtimestamp(arr)
            dep_time = dt.datetime.fromtimestamp(dep)

            # print(sid[:-1])
            if sid[:-1] not in my_stops:
                continue

            train_map[route].append(
                {
                    "stop_name": my_stops[sid[:-1]],
                    "train": sid,
                    "is_uptown": "N" in sid,
                    "arrival_time": arr_time,
                }
            )

    time = dt.datetime.now()
    for train in train_map:
        print(f"Train: {train}")
        stops = train_map[train]
        for stop in stops:
            arr = stop["arrival_time"]
            stop = stop["stop_name"]

            if "N" in sid and time < arr:
                print(
                    f"Stop: {stop}, Train: {train}, uptown, arrival time: {arr.strftime("%H:%M:%S")} (in {arr - time}"
                )
            elif time < arr:
                print(
                    f"Stop: {stop}, Train: {train}, downtown, arrival time: {arr.strftime("%H:%M:%S")} (in {arr - time})"
                )
