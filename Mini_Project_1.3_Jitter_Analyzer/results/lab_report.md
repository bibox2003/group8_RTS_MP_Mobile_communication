# Jitter Lab: Real-Time Timing Under Simulated Noise

## Aim and method

This experiment measured a periodic Python job over 200 releases
with a nominal period of 50.0 ms and a relative
deadline of 90% of the period. The loop scheduled
each target release from an absolute time to limit accumulated drift.
Each configuration was compared using release jitter, completion jitter,
response time, and the fraction of jobs meeting their assigned deadlines.

## Baseline

The unloaded run measured a release-jitter standard deviation of
4.163 ms and a maximum absolute release
jitter of 56.011 ms. Its completion-jitter
standard deviation was 6.096 ms.
The deadline-hit fraction was
100.0%.

## Main finding

Among configurations with at least 95% deadline hits, **Delay 4 ms** had the largest release jitter standard deviation (6.520 ms) and a deadline-hit fraction of 100.0%. This illustrates that deadline-hit rate and jitter describe different timing properties.

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
