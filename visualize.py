import sys
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


def plot_views(df):
    channels = df["ChannelName"].unique()

    fig, ax = plt.subplots(figsize=(12, 6))

    for channel in channels:
        channel_df = df[df["ChannelName"] == channel].sort_values("Date")
        ax.plot(
            channel_df["Date"],
            channel_df["Views"],
            marker="o",
            linewidth=2,
            markersize=5,
            label=channel,
        )

    ax.set_title("YouTube Channel Views Over Time", fontsize=16, fontweight="bold", pad=16)
    ax.set_xlabel("Date", fontsize=12)
    ax.set_ylabel("Total Views", fontsize=12)

    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d"))
    ax.xaxis.set_major_locator(mdates.AutoDateLocator())
    fig.autofmt_xdate(rotation=45)

    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{x:,.0f}"))

    ax.legend(title="Channel", fontsize=10, title_fontsize=11, loc="upper left")
    ax.grid(True, linestyle="--", alpha=0.6)
    ax.set_axisbelow(True)

    fig.tight_layout()
    fig.savefig(OUTPUT_FILE, dpi=150, bbox_inches="tight")
    print(f"Chart saved to {OUTPUT_FILE}")
    plt.show()


def main():
    df = load_data(CSV_FILE)

    if df.empty:
        print("No data found in cumulative_stats.csv.")
        return

    print(f"Loaded {len(df)} rows across {df['ChannelName'].nunique()} channel(s).")
    plot_views(df)


if __name__ == "__main__":
    main()
