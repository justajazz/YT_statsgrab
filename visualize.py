import matplotlib
matplotlib.use('Agg')
import os
import sys
import requests
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

from sheets_client import get_sheet

OUTPUT_FILE = "growth_chart.png"


def load_data():
    sheet = get_sheet()
    rows = sheet.get_all_values()
    if len(rows) < 2:
        print("Error: Google Sheet has no data. Run main.py first to collect data.")
        sys.exit(1)

    df = pd.DataFrame(rows[1:], columns=rows[0])
    df["Date"] = pd.to_datetime(df["Date"])
    df["Views"] = pd.to_numeric(df["Views"], errors="coerce")
    df["Subscribers"] = pd.to_numeric(df["Subscribers"], errors="coerce")
    df["Videos"] = pd.to_numeric(df["Videos"], errors="coerce")
    return df


def group_by_day(df):
    """Keep only the maximum Views value per channel per calendar day."""
    daily = (
        df.groupby(["ChannelName", df["Date"].dt.date])["Views"]
        .max()
        .reset_index()
    )
    daily["Date"] = pd.to_datetime(daily["Date"])
    return daily


def build_stats_message(df):
    """Build an HTML-formatted stats table with deltas vs previous record."""
    dates = sorted(df["Date"].dt.date.unique())
    latest_date = dates[-1]
    prev_date = dates[-2] if len(dates) >= 2 else None

    latest_df = df[df["Date"].dt.date == latest_date].drop_duplicates(subset="ChannelName", keep="last")
    prev_df = df[df["Date"].dt.date == prev_date].drop_duplicates(subset="ChannelName", keep="last") if prev_date else None

    def fmt_delta(delta):
        if delta is None:
            return ""
        sign = "+" if delta >= 0 else ""
        return f" ({sign}{delta:,})"

    def fmt_int(val):
        if pd.isna(val):
            return None
        return int(val)

    lines = [f"📊 <b>Stats — {latest_date}</b>\n"]

    for _, row in latest_df.iterrows():
        name = row["ChannelName"]
        subs = fmt_int(row["Subscribers"])
        views = fmt_int(row["Views"])
        videos = fmt_int(row["Videos"])

        subs_delta = views_delta = videos_delta = None
        if prev_df is not None:
            prev_row = prev_df[prev_df["ChannelName"] == name]
            if not prev_row.empty:
                pr = prev_row.iloc[0]
                if views is not None and pd.notna(pr["Views"]):
                    views_delta = views - int(pr["Views"])
                if videos is not None and pd.notna(pr["Videos"]):
                    videos_delta = videos - int(pr["Videos"])
                if subs is not None and pd.notna(pr["Subscribers"]):
                    subs_delta = subs - int(pr["Subscribers"])

        subs_str = f"{subs:,}{fmt_delta(subs_delta)}" if subs is not None else "Hidden"
        views_str = f"{views:,}{fmt_delta(views_delta)}" if views is not None else "—"
        videos_str = f"{videos:,}{fmt_delta(videos_delta)}" if videos is not None else "—"

        lines.append(f"<b>{name}</b>")
        lines.append(f"  👥 Subscribers: {subs_str}")
        lines.append(f"  👁 Views:       {views_str}")
        lines.append(f"  🎬 Videos:      {videos_str}")
        lines.append("")

    return "\n".join(lines).rstrip()


def send_to_telegram(image_path, stats_text=None):
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        print("Telegram: BOT_TOKEN or CHAT_ID not set, skipping notification")
        return

    base_url = f"https://api.telegram.org/bot{token}"

    try:
        if stats_text:
            resp = requests.post(
                f"{base_url}/sendMessage",
                data={"chat_id": chat_id, "text": stats_text, "parse_mode": "HTML"},
                timeout=10,
            )
            if not resp.ok:
                print(f"Telegram: Failed to send stats text ({resp.status_code})")

        with open(image_path, "rb") as photo:
            resp = requests.post(
                f"{base_url}/sendPhoto",
                data={"chat_id": chat_id},
                files={"photo": photo},
                timeout=10,
            )
        if resp.ok:
            print("Telegram: Chart sent successfully")
        else:
            print(f"Telegram: Failed to send chart ({resp.status_code})")
    except requests.exceptions.ConnectionError:
        print("Telegram: No connection, skipping notification")


def plot_views(df):
    channels = df["ChannelName"].unique()
    n_channels = len(channels)
    daily = group_by_day(df)

    # n_channels rows for absolute views + 1 row for % growth
    n_rows = n_channels + 1
    fig, axes = plt.subplots(n_rows, 1, figsize=(12, 5 * n_rows))
    if n_rows == 1:
        axes = [axes]

    colors = plt.rcParams["axes.prop_cycle"].by_key()["color"]

    # --- One subplot per channel (absolute views) ---
    for i, channel in enumerate(channels):
        ax = axes[i]
        color = colors[i % len(colors)]
        channel_df = daily[daily["ChannelName"] == channel].sort_values("Date")

        ax.plot(
            channel_df["Date"],
            channel_df["Views"],
            marker="o",
            linewidth=2,
            markersize=5,
            color=color,
            label=channel,
        )

        ax.set_title(f"{channel} — Views Over Time", fontsize=13, fontweight="bold")
        ax.set_xlabel("Date", fontsize=11)
        ax.set_ylabel("Total Views", fontsize=11)
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d"))
        ax.xaxis.set_major_locator(mdates.AutoDateLocator())
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{x:,.0f}"))
        ax.grid(True, linestyle="--", alpha=0.6)
        ax.set_axisbelow(True)
        ax.legend(fontsize=10, loc="upper left")

    # --- Combined % growth subplot ---
    ax_pct = axes[-1]
    for i, channel in enumerate(channels):
        color = colors[i % len(colors)]
        channel_df = daily[daily["ChannelName"] == channel].sort_values("Date").dropna(subset=["Views"])

        if channel_df.empty or channel_df["Views"].iloc[0] == 0:
            continue

        base = channel_df["Views"].iloc[0]
        pct_growth = ((channel_df["Views"] - base) / base) * 100

        ax_pct.plot(
            channel_df["Date"],
            pct_growth,
            marker="o",
            linewidth=2,
            markersize=5,
            color=color,
            label=channel,
        )

    ax_pct.axhline(0, color="gray", linewidth=0.8, linestyle="-")
    ax_pct.set_title("Views — % Growth from Start", fontsize=13, fontweight="bold")
    ax_pct.set_xlabel("Date", fontsize=11)
    ax_pct.set_ylabel("Growth (%)", fontsize=11)
    ax_pct.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d"))
    ax_pct.xaxis.set_major_locator(mdates.AutoDateLocator())
    ax_pct.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{x:+.1f}%"))
    ax_pct.grid(True, linestyle="--", alpha=0.6)
    ax_pct.set_axisbelow(True)
    ax_pct.legend(title="Channel", fontsize=10, title_fontsize=11, loc="upper left")

    fig.suptitle("YouTube Channel Growth", fontsize=16, fontweight="bold")
    fig.tight_layout()
    fig.autofmt_xdate(rotation=45)

    fig.savefig(OUTPUT_FILE, dpi=150, bbox_inches="tight")
    print(f"Chart saved to {OUTPUT_FILE}")
    plt.close(fig)


def main():
    df = load_data()

    if df.empty:
        print("No data found in Google Sheet.")
        return

    print(f"Loaded {len(df)} rows across {df['ChannelName'].nunique()} channel(s).")
    plot_views(df)
    stats_text = build_stats_message(df)
    send_to_telegram(OUTPUT_FILE, stats_text)


if __name__ == "__main__":
    main()
