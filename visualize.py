import matplotlib
matplotlib.use('Agg')
import os
import sys
import requests
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

CSV_FILE = "cumulative_stats.csv"
OUTPUT_FILE = "growth_chart.png"


def load_data(csv_file):
    try:
        df = pd.read_csv(csv_file, parse_dates=["Date"])
    except FileNotFoundError:
        print(f"Error: {csv_file} not found. Run main.py first to collect data.")
        sys.exit(1)

    # Coerce numeric columns; "Hidden" subscriber counts become NaN
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


def send_to_telegram(image_path):
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        print("Telegram: BOT_TOKEN or CHAT_ID not set, skipping notification")
        return
    url = f"https://api.telegram.org/bot{token}/sendPhoto"
    try:
        with open(image_path, "rb") as photo:
            response = requests.post(url, data={"chat_id": chat_id}, files={"photo": photo}, timeout=10)
        if response.ok:
            print("Telegram: Chart sent successfully")
        else:
            print(f"Telegram: Failed to send ({response.status_code})")
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
    send_to_telegram(OUTPUT_FILE)


def main():
    df = load_data(CSV_FILE)

    if df.empty:
        print("No data found in cumulative_stats.csv.")
        return

    print(f"Loaded {len(df)} rows across {df['ChannelName'].nunique()} channel(s).")
    plot_views(df)


if __name__ == "__main__":
    main()
