# Mini Project 1.3: Real-Time Jitter Analyzer

A Python simulation that measures periodic-task release jitter, completion jitter, response time, and deadline-hit rate under three controllable disturbances.

## Run the experiment

Requires Python 3.9 or later.

1. Open a terminal in this folder.
2. Install the two dependencies:

       python3 -m pip install -r requirements.txt

3. Run the experiment:

       python3 jitter_lab.py

The script runs 200 jobs for each of 13 configurations and saves its table, report, and plots in the results folder. A complete run takes around two minutes on a typical laptop.

## Disturbances

- Background CPU load at 25%, 50%, and 75% duty cycle.
- Occasional dispatch delays with varied probability and magnitude.
- Variable job workload with 10%, 30%, and 50% spread.

The timing loop schedules releases against absolute target times to limit accumulated drift. Release jitter is actual release minus ideal release. Completion jitter is the change in consecutive completion intervals relative to the nominal period. Deadline hits compare each response time against the assigned relative deadline.

## Deliverables

- jitter_lab.py: experiment implementation and plot/report generation.
- results/summary.csv: measurements for all configurations.
- results/lab_report.md: summary, findings, and interpretation.
- results/cpu_load_sweep.png: CPU-load sweep.
- results/delay_sweeps.png: injected-delay probability and magnitude sweeps.
- results/workload_sweep.png: workload-variation sweep.
- results/jitter_vs_deadlines.png: comparison of release jitter and deadline-hit fraction.

This is a teaching simulation on a general-purpose operating system. Its results illustrate timing concepts and do not provide certified worst-case timing guarantees.
