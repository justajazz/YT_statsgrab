import os
import re
import csv
import requests
from datetime import datetime

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

    # Append to cumulative CSV
    csv_file = "cumulative_stats.csv"
    file_exists = os.path.exists(csv_file)
    today = datetime.now().strftime("%Y-%m-%d")
    with open(csv_file, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f, fieldnames=["Date", "ChannelName", "Views", "Subscribers", "Videos"]
        )
        if not file_exists:
            writer.writeheader()
        for r in results:
            writer.writerow({
                "Date": today,
                "ChannelName": r["name"],
                "Views": r["views"],
                "Subscribers": r["subscribers"],
                "Videos": r["videos"],
            })
    print(f"\nAppended {len(results)} row(s) to {csv_file}")


if __name__ == "__main__":
    main()
