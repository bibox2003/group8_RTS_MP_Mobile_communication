"""A small lab for measuring timing jitter under simulated system noise."""

import time
import threading
import random
import csv
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt


# Keep experiments repeatable so different runs can be compared.
RANDOM_SEED = 17
random.seed(RANDOM_SEED)
np.random.seed(RANDOM_SEED)

# The simulator will run 200 jobs in each experiment.
PERIOD_SECONDS = 0.05
RELATIVE_DEADLINE = 0.90
JOB_COUNT = 200

OUTPUT_DIR = Path("results")
OUTPUT_DIR.mkdir(exist_ok=True)

def do_job(work_units: int) -> int:
    """Do repeatable work; larger inputs take longer."""
    value = 0
    for i in range(work_units):
        value = (value * 33 + i * i) % 1_000_003
    return value


def run_background_load(stop_event: threading.Event, duty_cycle: float) -> None:
    """Add adjustable CPU interference until stop_event is set."""
    duty_cycle = max(0.0, min(1.0, duty_cycle))

    while not stop_event.is_set():
        busy_for = 0.004 * duty_cycle
        rest_for = 0.004 * (1.0 - duty_cycle)

        end_time = time.perf_counter() + busy_for
        while time.perf_counter() < end_time:
            # Small arithmetic loop to occupy the CPU.
            _ = 12345 * 67890

        if rest_for > 0:
            time.sleep(rest_for)
            
            
def run_experiment(
    *,
    name: str,
    load_intensity: float = 0.0,
    extra_delay_probability: float = 0.0,
    extra_delay_seconds: float = 0.0,
    workload_spread: float = 0.0,
) -> dict:
    """Run periodic jobs and record release, completion, and deadline data."""
    stop_event = threading.Event()
    load_thread = None

    if load_intensity > 0:
        load_thread = threading.Thread(
            target=run_background_load,
            args=(stop_event, load_intensity),
            daemon=True,
        )
        load_thread.start()

    ideal_releases = []
    actual_releases = []
    completions = []
    response_times = []
    deadline_misses = []

    period = PERIOD_SECONDS
    deadline = RELATIVE_DEADLINE * period
    first_release = time.perf_counter() + 0.2

    try:
        for job_index in range(JOB_COUNT):
            ideal_release = first_release + job_index * period

            # Sleep to an absolute target so small delays don't accumulate.
            remaining = ideal_release - time.perf_counter()
            if remaining > 0:
                time.sleep(remaining)

                        # Occasionally delay when the job starts.
            # Occasionally delay the job's actual start.
            if random.random() < extra_delay_probability:
                time.sleep(extra_delay_seconds)

            # Record the actual start after any simulated delay.
            actual_release = time.perf_counter()

            # Vary the workload to simulate execution-time variation.
            work_units = 12_000
            if workload_spread > 0:
                work_units = max(
                    1,
                    int(random.gauss(work_units, work_units * workload_spread)),
                )

            do_job(work_units)
            completion = time.perf_counter()
            response = completion - actual_release

            ideal_releases.append(ideal_release)
            actual_releases.append(actual_release)
            completions.append(completion)
            response_times.append(response)
            deadline_misses.append(response > deadline)
    finally:
        stop_event.set()
        if load_thread is not None:
            load_thread.join(timeout=1)

    ideal_releases = np.array(ideal_releases)
    actual_releases = np.array(actual_releases)
    completions = np.array(completions)
    response_times = np.array(response_times)
    deadline_misses = np.array(deadline_misses)

    # Release jitter is the actual release's offset from its ideal target.
    release_jitter = actual_releases - ideal_releases

    # Output jitter tracks how much each completion-to-completion interval
    # differs from the task's nominal period. The first job has no interval.
    completion_jitter = np.zeros(JOB_COUNT)
    completion_jitter[1:] = np.diff(completions) - period

    return {
        "name": name,
        "period": period,
        "deadline": deadline,
        "ideal_releases": ideal_releases,
        "actual_releases": actual_releases,
        "completions": completions,
        "response_times": response_times,
        "deadline_misses": deadline_misses,
        "release_jitter": release_jitter,
        "completion_jitter": completion_jitter,
    }
    
def summarize(result: dict) -> dict:
    """Calculate the key timing and deadline-hit measurements."""
    release_jitter = result["release_jitter"]
    completion_jitter = result["completion_jitter"]
    response_times = result["response_times"]

    return {
        "name": result["name"],
        "release_jitter_std_ms": float(np.std(release_jitter) * 1000),
        "release_jitter_max_ms": float(np.max(np.abs(release_jitter)) * 1000),
        "completion_jitter_std_ms": float(np.std(completion_jitter) * 1000),
        "completion_jitter_max_ms": float(np.max(np.abs(completion_jitter)) * 1000),
        "deadline_hit_fraction": float(np.mean(~result["deadline_misses"])),
        "mean_response_ms": float(np.mean(response_times) * 1000),
        "max_response_ms": float(np.max(response_times) * 1000),
    }
    
def run_sweep() -> list[dict]:
    """Run a baseline and three settings for each disturbance."""
    experiments = [
        {"name": "Baseline"},
        {"name": "Load 25%", "load_intensity": 0.25},
        {"name": "Load 50%", "load_intensity": 0.50},
        {"name": "Load 75%", "load_intensity": 0.75},
        {"name": "Delay chance 5%", "extra_delay_probability": 0.05,
         "extra_delay_seconds": 0.008},
        {"name": "Delay chance 15%", "extra_delay_probability": 0.15,
         "extra_delay_seconds": 0.008},
        {"name": "Delay chance 30%", "extra_delay_probability": 0.30,
         "extra_delay_seconds": 0.008},
        {"name": "Delay 4 ms", "extra_delay_probability": 0.10,
         "extra_delay_seconds": 0.004},
        {"name": "Delay 8 ms", "extra_delay_probability": 0.10,
         "extra_delay_seconds": 0.008},
        {"name": "Delay 12 ms", "extra_delay_probability": 0.10,
         "extra_delay_seconds": 0.012},
        {"name": "Work spread 10%", "workload_spread": 0.10},
        {"name": "Work spread 30%", "workload_spread": 0.30},
        {"name": "Work spread 50%", "workload_spread": 0.50},
    ]

    results = []
    for settings in experiments:
        print(f"Running {settings['name']}...")
        results.append(run_experiment(**settings))

    return results

def save_summary_table(results: list[dict]) -> list[dict]:
    """Print the experiment summary and save it as a CSV file."""
    summaries = [summarize(result) for result in results]
    csv_path = OUTPUT_DIR / "summary.csv"

    with csv_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=summaries[0].keys())
        writer.writeheader()
        writer.writerows(summaries)

    print("\nJITTER LAB RESULTS")
    print("-" * 88)
    print(
        f"{'Experiment':<22} {'Rel. jitter SD':>14} {'Out. jitter SD':>14} "
        f"{'Deadline hits':>14} {'Mean response':>15}"
    )
    print("-" * 88)

    for row in summaries:
        print(
            f"{row['name']:<22} "
            f"{row['release_jitter_std_ms']:>11.3f} ms "
            f"{row['completion_jitter_std_ms']:>11.3f} ms "
            f"{row['deadline_hit_fraction'] * 100:>12.1f}% "
            f"{row['mean_response_ms']:>12.3f} ms"
        )

    print(f"\nSaved results table to: {csv_path}")
    return summaries

def make_plots(summaries: list[dict]) -> None:
    """Save disturbance sweep plots and a jitter/deadline comparison."""
    blue = "#2563EB"
    orange = "#EA580C"
    green = "#15803D"
    baseline = next(r for r in summaries if r["name"] == "Baseline")

    # Background CPU load sweep.
    rows = [r for r in summaries if r["name"].startswith("Load ")]
    rows.sort(key=lambda r: float(r["name"].split()[1].replace("%", "")))
    x = [float(r["name"].split()[1].replace("%", "")) for r in rows]
    y = [r["release_jitter_std_ms"] for r in rows]

    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.plot(x, y, marker="o", linewidth=2.5, color=blue, label="CPU load")
    ax.axhline(baseline["release_jitter_std_ms"], color="black",
               linestyle="--", label="Baseline")
    ax.set(title="Background CPU Load vs Release Jitter",
           xlabel="Background load intensity (%)",
           ylabel="Release jitter standard deviation (ms)")
    ax.grid(alpha=0.25)
    ax.legend()
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "cpu_load_sweep.png", dpi=180)
    plt.close(fig)

    # Injected delay sweeps: chance and magnitude.
    chance = [r for r in summaries if r["name"].startswith("Delay chance")]
    chance.sort(key=lambda r: float(r["name"].split()[2].replace("%", "")))
    chance_x = [float(r["name"].split()[2].replace("%", "")) for r in chance]
    chance_y = [r["release_jitter_std_ms"] for r in chance]

    magnitude = [
        r for r in summaries
        if r["name"].startswith("Delay ") and "ms" in r["name"]
    ]
    magnitude.sort(key=lambda r: float(r["name"].split()[1]))
    magnitude_x = [float(r["name"].split()[1]) for r in magnitude]
    magnitude_y = [r["release_jitter_std_ms"] for r in magnitude]

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))
    axes[0].plot(chance_x, chance_y, marker="o", color=orange)
    axes[0].set(title="Varying Delay Chance", xlabel="Chance of delay (%)",
                ylabel="Release jitter SD (ms)")
    axes[1].plot(magnitude_x, magnitude_y, marker="o", color=orange)
    axes[1].set(title="Varying Delay Magnitude", xlabel="Injected delay (ms)",
                ylabel="Release jitter SD (ms)")
    for ax in axes:
        ax.axhline(baseline["release_jitter_std_ms"], color="black",
                   linestyle="--", label="Baseline")
        ax.grid(alpha=0.25)
        ax.legend()
    fig.suptitle("Interrupt-Like Start Delays")
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "delay_sweeps.png", dpi=180)
    plt.close(fig)

    # Variable workload sweep.
    rows = [r for r in summaries if r["name"].startswith("Work spread")]
    rows.sort(key=lambda r: float(r["name"].split()[2].replace("%", "")))
    x = [float(r["name"].split()[2].replace("%", "")) for r in rows]
    y = [r["completion_jitter_std_ms"] for r in rows]

    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.plot(x, y, marker="o", linewidth=2.5, color=green, label="Work variation")
    ax.axhline(baseline["completion_jitter_std_ms"], color="black",
               linestyle="--", label="Baseline")
    ax.set(title="Workload Variation vs Completion Jitter",
           xlabel="Workload spread (%)",
           ylabel="Completion jitter standard deviation (ms)")
    ax.grid(alpha=0.25)
    ax.legend()
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "workload_sweep.png", dpi=180)
    plt.close(fig)

    # Compare release jitter with the fraction of jobs meeting deadlines.
    fig, ax = plt.subplots(figsize=(9, 5.5))
    for row in summaries:
        hit_percent = row["deadline_hit_fraction"] * 100
        ax.scatter(row["release_jitter_std_ms"], hit_percent,
                   s=70, color=blue, edgecolor="white")
        ax.annotate(
            row["name"],
            (row["release_jitter_std_ms"], hit_percent),
            xytext=(5, 5), textcoords="offset points", fontsize=7,
        )
    ax.axhline(95, color=orange, linestyle="--",
               label="95% deadline-hit reference")
    ax.set(title="Jitter and Deadline Hits Are Different Measures",
           xlabel="Release jitter standard deviation (ms)",
           ylabel="Jobs meeting assigned deadline (%)",
           ylim=(0, 105))
    ax.grid(alpha=0.2)
    ax.legend()
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "jitter_vs_deadlines.png", dpi=180)
    plt.close(fig)

    print(f"Saved four plots in: {OUTPUT_DIR}")
    
def save_lab_report(summaries: list[dict]) -> None:
    """Write a short report using the measurements from this run."""
    baseline = next(r for r in summaries if r["name"] == "Baseline")
    high_jitter = max(
        (r for r in summaries if r["deadline_hit_fraction"] >= 0.95),
        key=lambda r: r["release_jitter_std_ms"],
        default=None,
    )

    if high_jitter is None:
        comparison = (
            "No tested configuration reached a 95% deadline-hit fraction. "
            "Review the measured table and plots when interpreting this run."
        )
    else:
        comparison = (
            f"Among configurations with at least 95% deadline hits, "
            f"**{high_jitter['name']}** had the largest release jitter "
            f"standard deviation ({high_jitter['release_jitter_std_ms']:.3f} ms) "
            f"and a deadline-hit fraction of "
            f"{high_jitter['deadline_hit_fraction'] * 100:.1f}%. "
            "This illustrates that deadline-hit rate and jitter describe "
            "different timing properties."
        )

    report = f"""# Jitter Lab: Real-Time Timing Under Simulated Noise

## Aim and method

This experiment measured a periodic Python job over {JOB_COUNT} releases
with a nominal period of {PERIOD_SECONDS * 1000:.1f} ms and a relative
deadline of {RELATIVE_DEADLINE * 100:.0f}% of the period. The loop scheduled
each target release from an absolute time to limit accumulated drift.
Each configuration was compared using release jitter, completion jitter,
response time, and the fraction of jobs meeting their assigned deadlines.

## Baseline

The unloaded run measured a release-jitter standard deviation of
{baseline['release_jitter_std_ms']:.3f} ms and a maximum absolute release
jitter of {baseline['release_jitter_max_ms']:.3f} ms. Its completion-jitter
standard deviation was {baseline['completion_jitter_std_ms']:.3f} ms.
The deadline-hit fraction was
{baseline['deadline_hit_fraction'] * 100:.1f}%.

## Main finding

{comparison}

## Disturbance interpretation

The background arithmetic thread approximates general CPU interference and
OS scheduling noise. The occasional injected delay approximates delayed task
dispatch, such as an interrupt-like disturbance. Varying the workload size
approximates execution-time changes associated with cache, pipeline, or
data-dependent effects.

These are teaching analogies. Python sleeps, threads, and a general-purpose
operating system do not reproduce hardware interrupts, DMA, cache behavior,
or a real-time scheduler precisely. The measurements therefore illustrate
timing concepts; they are not certified worst-case guarantees.

## Figures and data

The run also saves `summary.csv`, `cpu_load_sweep.png`, `delay_sweeps.png`,
`workload_sweep.png`, and `jitter_vs_deadlines.png` in the `results` folder.
The CSV and figures are generated from the same recorded experiment results.
"""
    report_path = OUTPUT_DIR / "lab_report.md"
    report_path.write_text(report, encoding="utf-8")
    print(f"Saved lab report to: {report_path}")
    
def main() -> None:
    results = run_sweep()
    summaries = save_summary_table(results)
    make_plots(summaries)
    save_lab_report(summaries)


if __name__ == "__main__":
    main()
