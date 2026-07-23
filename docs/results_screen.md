# Results screen

Results is a dedicated end-of-run state. It identifies the scenario, run ID, simulated duration, and seed, then shows scheduled, arrived, completed, unfinished-at-closing, average/p90 wait, visit duration, satisfaction, low-satisfaction count, and overtime.

Six tabs organise detail:

1. Summary — calculated findings, replay-period selection, results CSV, and GIF export.
2. Bottlenecks — ranked stage cards, score components, queues, waits, peak times, utilisation, and findings.
3. Patient flow — population, initial/examination/return phases, departmental queues, doctor queues, arrivals, and completions.
4. Resources — utilisation, busy/idle capacity, overtime, and common-seed scenario comparison.
5. Satisfaction — distribution and relationship with waiting.
6. Patient records — downloadable synthetic records, table, and selected journey timeline.

Replay periods are deterministic: the whole run, a one-hour window around the largest combined sampled queue, the strongest 15-minute examination-return bin plus surrounding context, and the final hour.
