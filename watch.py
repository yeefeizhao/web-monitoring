#!/usr/bin/env python3
"""
Website change monitor (single-run, for GitHub Actions).
Reads config from environment variables set in the workflow.
"""

import hashlib
import os
import sys

import requests
from bs4 import BeautifulSoup

URL = os.environ["WATCH_URL"]
SELECTOR = os.environ.get("WATCH_SELECTOR") or None
NTFY_TOPIC = os.environ["NTFY_TOPIC"]
STATE_FILE = "last_hash.txt"


def fetch_content():
    headers = {"User-Agent": "Mozilla/5.0 (change-monitor)"}
    resp = requests.get(URL, headers=headers, timeout=30)
    resp.raise_for_status()
    if SELECTOR:
        soup = BeautifulSoup(resp.text, "html.parser")
        el = soup.select_one(SELECTOR)
        if el is None:
            raise RuntimeError(f"Selector {SELECTOR!r} not found on the page")
        return el.get_text(strip=True)
    return resp.text


def notify(message):
    requests.post(
        f"https://ntfy.sh/{NTFY_TOPIC}",
        data=message.encode("utf-8"),
        headers={"Title": "Site updated", "Click": URL, "Tags": "bell"},
        timeout=30,
    )


def main():
    try:
        current = hashlib.sha256(fetch_content().encode("utf-8")).hexdigest()
    except Exception as e:
        # Skip this cycle on transient errors; check the Actions tab if alerts stop.
        print(f"check failed: {e}", file=sys.stderr)
        sys.exit(0)

    last = None
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            last = f.read().strip()

    if last is None:
        print("baseline saved")
    elif current != last:
        print("CHANGE detected -> notifying")
        notify(f"{URL} changed")
    else:
        print("no change")
        return  # nothing to write, so no commit is made

    with open(STATE_FILE, "w") as f:
        f.write(current)


if __name__ == "__main__":
    main()
