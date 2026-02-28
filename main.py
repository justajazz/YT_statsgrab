import os
import re
import subprocess
import sys
import requests
from datetime import datetime

from sheets_client import get_sheet

YOUTUBE_API_URL = "https://www.googleapis.com/youtube/v3/channels"


def get_api_key():
    key = os.environ.get("YOUTUBE_API_KEY")
    if not key:
        key = input("Enter your YouTube API key: ").strip()
    return key


def parse_channel_line(line):
    """Parse a line from channels.txt into (type, value).
    Supports: channel IDs, @handles, full URLs, legacy usernames.
    """
    line = line.strip()
    if not line or line.startswith("#"):
        return None, None

    # Full channel ID (UCxxxxxxxxxx)
    if re.match(r"^UC[\w-]{22}$", line):
        return "id", line

    # URL containing channel ID
    match = re.search(r"youtube\.com/channel/(UC[\w-]{22})", line)
    if match:
        return "id", match.group(1)

    # URL with @handle
    match = re.search(r"youtube\.com/@([\w.-]+)", line)
    if match:
        return "handle", match.group(1)

    # Bare @handle
    if line.startswith("@"):
        return "handle", line[1:]

    # Fall back to legacy username
    return "username", line


def fetch_channel_stats(api_key, channel_type, channel_value):
    params = {"part": "snippet,statistics", "key": api_key}

    if channel_type == "id":
        params["id"] = channel_value
    elif channel_type == "handle":
        params["forHandle"] = channel_value
    else:
        params["forUsername"] = channel_value

    response = requests.get(YOUTUBE_API_URL, params=params)
    response.raise_for_status()
    data = response.json()

    if not data.get("items"):
        return None

    item = data["items"][0]
    stats = item["statistics"]
    snippet = item["snippet"]

    return {
        "channel_id": item["id"],
        "name": snippet["title"],
        "views": int(stats.get("viewCount", 0)),
        "subscribers": (
            int(stats["subscriberCount"])
            if not stats.get("hiddenSubscriberCount")
            else "Hidden"
        ),
        "videos": int(stats.get("videoCount", 0)),
    }


def main():
    api_key = get_api_key()

    if not os.path.exists("channels.txt"):
        print("Error: channels.txt not found.")
        return

    with open("channels.txt", encoding="utf-8") as f:
        lines = f.readlines()

    results = []
    for line in lines:
        channel_type, channel_value = parse_channel_line(line)
        if not channel_type:
            continue

        print(f"Fetching {channel_value} ...", end=" ", flush=True)
        try:
            stats = fetch_channel_stats(api_key, channel_type, channel_value)
            if stats:
                results.append(stats)
                print(f"OK  ({stats['name']})")
            else:
                print("not found")
        except requests.HTTPError as e:
            print(f"HTTP error: {e}")

    if not results:
        print("No results to display.")
        return

    # Console table
    print("\n" + "=" * 72)
    print(f"{'Channel':<32} {'Views':>14} {'Subscribers':>14} {'Videos':>8}")
    print("-" * 72)
    for r in results:
        subs = f"{r['subscribers']:,}" if isinstance(r["subscribers"], int) else r["subscribers"]
        print(f"{r['name']:<32} {r['views']:>14,} {subs:>14} {r['videos']:>8,}")
    print("=" * 72)

    # Append to Google Sheet
    today = datetime.now().strftime("%Y-%m-%d")
    sheet = get_sheet()
    if not sheet.get_all_values():
        sheet.append_row(["Date", "ChannelName", "Views", "Subscribers", "Videos"])
    rows = [
        [today, r["name"], r["views"], r["subscribers"], r["videos"]]
        for r in results
    ]
    sheet.append_rows(rows)
    print(f"\nAppended {len(results)} row(s) to Google Sheet")

    # Trigger visualize.py automatically after a successful data collection
    subprocess.run([sys.executable, "visualize.py"], check=True)


if __name__ == "__main__":
    main()
