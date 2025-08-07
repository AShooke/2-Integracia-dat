import os
import sys
import io
import csv
import json
import time
import logging
from datetime import datetime
from itertools import product

import requests
import pytz
from apscheduler.schedulers.blocking import BlockingScheduler

from config import API_URL, API_KEY, OUTPUT_DIR, TIMEZONE, DISTRICTS, LATLNG, RANGE, LIMIT, OFFSET, UPDATED_SINCE, SCHEDULED_TIMES

if isinstance(TIMEZONE, str):
    TIMEZONE = pytz.timezone(TIMEZONE)

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', line_buffering=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("golemio_extractor.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("GolemioExtractor")

WEEKDAY = {1: "Mon", 2: "Tue", 3: "Wed", 4: "Thu", 5: "Fri", 6: "Sat", 7: "Sun"}


def fetch_data(latlng=None, range_m=None, districts=None, limit=100, offset=0, updated_since=None):
    headers = {"X-Access-Token": API_KEY}
    params = {
        "latlng": latlng or "50.124935,14.457204",
        "range": range_m or 10000,
        "districts": ",".join(districts) if districts else "praha-4",
        "limit": limit,
        "offset": offset,
    }
    if updated_since:
        params["updatedSince"] = updated_since

    all_features = []
    total_fetched = 0
    while True:
        logger.info(f"Requesting URL: {API_URL}")
        logger.info(f"Params: {params}")
        resp = requests.get(API_URL, headers=headers, params=params, timeout=15)

        logger.info(f"Response status: {resp.status_code}")

        if resp.status_code == 429:
            retry = int(resp.headers.get("Retry-After", "60"))
            logger.warning(f"Rate limit hit, retrying in {retry}s")
            time.sleep(retry)
            continue

        resp.raise_for_status()
        payload = resp.json()

        features = payload.get("features", [])
        if not features:
            logger.info("No more features returned by API.")
            break

        # Enforce global limit
        remaining = limit - total_fetched
        if remaining <= 0:
            break
        if len(features) > remaining:
            features = features[:remaining]
        all_features.extend(features)
        total_fetched += len(features)
        logger.info(f"Received {len(features)} features; total so far: {len(all_features)}")

        if len(features) < params["limit"] or total_fetched >= limit:
            break

        params["offset"] += params["limit"]

    return all_features


def transform_feature(feature):
    props = feature.get("properties", {}) or {}
    addr = props.get("address", {}) or {}
    geom = feature.get("geometry", {}) or {}
    coords = geom.get("coordinates", [None, None])
    lon, lat = coords if len(coords) >= 2 else (None, None)

    kraj = props.get("district", "")

    opening = ""
    hours = props.get("opening_hours") or []
    if hours:
        first = hours[0]
        day = WEEKDAY.get(first.get("day_of_week"))
        opens = first.get("opens")
        if day and opens:
            opening = f"{day} {opens}"
        elif opens:
            opening = opens
        elif day:
            opening = day
        else:
            opening = ""
    else:
        opening = ""

    return {
        "id":            props.get("id", ""),
        "name":          props.get("name", ""),
        "street":        addr.get("street_address", ""),
        "psc":           addr.get("postal_code", ""),
        "city":          addr.get("address_locality", ""),
        "kraj":          kraj,
        "country":       addr.get("address_country", ""),
        "latitude":      lat,
        "longitude":     lon,
        "cas_otvorenia": opening,
    }


def save_data(rows, date_str):
    if not rows:
        logger.warning(f"No data to save for {date_str}, skipping file creation.")
        return None, None
    csv_dir = os.path.join(OUTPUT_DIR, "csv")
    json_dir = os.path.join(OUTPUT_DIR, "json")
    os.makedirs(csv_dir, exist_ok=True)
    os.makedirs(json_dir, exist_ok=True)
    fieldnames = [
        "ID knižnice",
        "Názov knižnice",
        "Ulica",
        "PSČ",
        "Mesto",
        "Kraj",
        "Krajina",
        "Zemepisná šírka",
        "Zemepisná dĺžka",
        "Čas otvorenia"
    ]

    # Always overwrite file, never append
    csv_path = os.path.join(csv_dir, f"libraries_{date_str}.csv")
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, lineterminator='\n')
        writer.writeheader()
        for row in rows:
            writer.writerow({
                "ID knižnice": row["id"],
                "Názov knižnice": row["name"],
                "Ulica": row["street"],
                "PSČ": row["psc"],
                "Mesto": row["city"],
                "Kraj": row["kraj"],
                "Krajina": row["country"],
                "Zemepisná šírka": row["latitude"],
                "Zemepisná dĺžka": row["longitude"],
                "Čas otvorenia": row["cas_otvorenia"]
            })
    logger.info(f"Saved CSV: {csv_path}")

    # Save JSON with slovak keys
    json_path = os.path.join(json_dir, f"libraries_{date_str}.json")
    json_rows = []
    for row in rows:
        json_rows.append({
            "ID knižnice": row["id"],
            "Názov knižnice": row["name"],
            "Ulica": row["street"],
            "PSČ": row["psc"],
            "Mesto": row["city"],
            "Kraj": row["kraj"],
            "Krajina": row["country"],
            "Zemepisná šírka": row["latitude"],
            "Zemepisná dĺžka": row["longitude"],
            "Čas otvorenia": row["cas_otvorenia"]
        })
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(json_rows, f, ensure_ascii=False, indent=2)
    logger.info(f"Saved JSON: {json_path}")

    return csv_path, json_path


def get_user_params():
    print("Enter districts separated by comma (e.g. praha-1,praha-2) or leave empty for default:")
    districts = input().strip()
    if districts:
        multi_districts = [[d.strip() for d in districts.split(",") if d.strip()]]
    else:
        multi_districts = [["praha-1"]]

    print("Enter coordinates lat,lng (e.g. 50.124935,14.457204) or leave empty for default:")
    latlng = input().strip()
    if latlng:
        multi_latlng = [latlng]
    else:
        multi_latlng = ["50.124935,14.457204"]

    print("Enter range in meters (e.g. 10000) or leave empty for default:")
    range_m = input().strip()
    if range_m:
        multi_range = [int(range_m)]
    else:
        multi_range = [10000]

    print("Enter limit (e.g. 10) or leave empty for default:")
    limit = input().strip()
    if limit:
        multi_limit = [int(limit)]
    else:
        multi_limit = [10]

    print("Enter offset (e.g. 0) or leave empty for default:")
    offset = input().strip()
    if offset:
        multi_offset = [int(offset)]
    else:
        multi_offset = [0]

    print("Enter updated_since (e.g. 2019-05-18T07:38:37.000Z) or leave empty for default:")
    updated_since = input().strip()
    if updated_since:
        multi_updated_since = [updated_since]
    else:
        multi_updated_since = ["2019-05-18T07:38:37.000Z"]

    return multi_districts, multi_latlng, multi_range, multi_limit, multi_offset, multi_updated_since


def generate_param_combinations():
    return list(product(
        [[d] for d in DISTRICTS],
        LATLNG,
        RANGE,
        LIMIT,
        OFFSET,
        UPDATED_SINCE
    ))


def run_extraction():
    now = datetime.now(TIMEZONE)
    date_str = now.strftime("%Y-%m-%d")
    logger.info(f"Starting extraction for {date_str}")

    param_combos = generate_param_combinations()
    all_rows = []
    global_limit = LIMIT[0] if LIMIT else None
    # Определяем координаты для сортировки, если заданы
    ref_lat, ref_lng = None, None
    if LATLNG and len(LATLNG) > 0:
        try:
            ref_lat, ref_lng = map(float, LATLNG[0].split(","))
        except Exception:
            ref_lat, ref_lng = None, None
    def distance(row):
        if ref_lat is None or ref_lng is None or not row["latitude"] or not row["longitude"]:
            return float('inf')
        try:
            lat = float(row["latitude"])
            lng = float(row["longitude"])
            return (lat - ref_lat) ** 2 + (lng - ref_lng) ** 2
        except Exception:
            return float('inf')

    for idx, (districts, latlng, range_m, limit, offset, updated_since) in enumerate(param_combos):
        logger.info(f"Extracting for combo {idx+1}/{len(param_combos)}: districts={districts}, latlng={latlng}, range={range_m}, limit={limit}, offset={offset}, updated_since={updated_since}")
        features = fetch_data(
            latlng=latlng,
            range_m=range_m,
            districts=districts,
            limit=10000,  # fetch all for this combo, filter later
            offset=offset,
            updated_since=updated_since
        )
        if not features:
            logger.warning(f"No features fetched for combo {idx+1}")
            continue
        rows = [transform_feature(feat) for feat in features]
        all_rows.extend(rows)
    if not all_rows:
        logger.error("No features fetched from API for any combination")
        return
    # Сортировка по расстоянию до заданной точки, если она есть, иначе по району и названию
    if ref_lat is not None and ref_lng is not None:
        all_rows.sort(key=distance)
    else:
        all_rows.sort(key=lambda x: (x['kraj'], x['name']))
    if global_limit is not None:
        all_rows = all_rows[:global_limit]
    save_data(all_rows, f"{date_str}_ALL")


if __name__ == "__main__":
    print("\n=== GOLEMIO EXTRACTOR ===\n")
    run_extraction()
    sched = BlockingScheduler(timezone=TIMEZONE)
    for hour, minute in SCHEDULED_TIMES:
        sched.add_job(run_extraction, 'cron', hour=hour, minute=minute)
    try:
        sched.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Scheduler stopped.")
