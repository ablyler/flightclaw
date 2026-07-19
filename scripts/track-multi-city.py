#!/usr/bin/env python3
"""Add a multi-city Google Flights itinerary to FlightClaw tracking."""

import argparse
import importlib.util
import json
import os
from datetime import datetime, timezone
from pathlib import Path

CHECK_PRICES = Path(__file__).with_name("check-prices.py")
spec = importlib.util.spec_from_file_location("flightclaw_check_prices", CHECK_PRICES)
if spec is None or spec.loader is None:
    raise RuntimeError(f"Cannot import {CHECK_PRICES}")
check_prices = importlib.util.module_from_spec(spec)
spec.loader.exec_module(check_prices)
check_route = check_prices.check_route
load_tracked = check_prices.load_tracked
save_tracked = check_prices.save_tracked


def parse_args():
    parser = argparse.ArgumentParser(description="Track a multi-city flight itinerary")
    parser.add_argument("--id", required=True, help="Stable tracking ID")
    parser.add_argument("--segments", required=True, help="JSON list of {origin,destination,date} slices")
    parser.add_argument("--flight-numbers", required=True, help="Comma-separated ordered flight numbers, without carrier prefix")
    parser.add_argument("--label", required=True)
    parser.add_argument("--target-price", type=float)
    parser.add_argument("--baseline-price", type=float, help="Known all-in itinerary total to record if the live lookup has no exact match")
    parser.add_argument("--exclude-basic", action="store_true")
    parser.add_argument("--stops", default="ANY", choices=("ANY", "NON_STOP", "ONE_STOP", "TWO_STOPS"))
    return parser.parse_args()


def main():
    args = parse_args()
    segments = json.loads(args.segments)
    if not isinstance(segments, list) or len(segments) < 2:
        raise SystemExit("--segments must contain at least two slices")
    for segment in segments:
        if not isinstance(segment, dict) or not all(segment.get(key) for key in ("origin", "destination", "date")):
            raise SystemExit("Each slice needs origin, destination, and date")

    tracked = load_tracked()
    if any(item.get("id") == args.id for item in tracked):
        raise SystemExit(f"Already tracking {args.id}")

    now = datetime.now(timezone.utc).isoformat()
    entry = {
        "id": args.id,
        "origin": segments[0]["origin"].upper(),
        "destination": segments[-1]["destination"].upper(),
        "date": segments[0]["date"],
        "return_date": None,
        "multi_city_segments": [
            {"origin": item["origin"].upper(), "destination": item["destination"].upper(), "date": item["date"]}
            for item in segments
        ],
        "flight_numbers": [item.strip() for item in args.flight_numbers.split(",") if item.strip()],
        "label": args.label,
        "cabin": "ECONOMY",
        "stops": args.stops,
        "target_price": args.target_price,
        "exclude_basic": args.exclude_basic,
        "currency": "USD",
        "added_at": now,
        "price_history": [],
    }
    price, airline, _, currency = check_route(entry)
    if price is None and args.baseline_price is not None:
        price = args.baseline_price
        airline = "manual-baseline"
    entry["currency"] = currency or "USD"
    entry["price_history"].append({"timestamp": now, "best_price": price, "airline": airline})
    tracked.append(entry)
    save_tracked(tracked)
    print(json.dumps({"id": entry["id"], "price": price, "currency": entry["currency"], "airline": airline}, indent=2))


if __name__ == "__main__":
    main()
