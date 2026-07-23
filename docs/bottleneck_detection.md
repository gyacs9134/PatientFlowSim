# Bottleneck detection

Bottleneck detection is deterministic and rule-based. For each visible stage, patient queue-entry and service-start timestamps create a five-minute queue series. The report calculates maximum and average queue, longest/average/p90 wait, peak time, utilisation, minutes above capacity, and affected-patient count.

## Ranking formula

The 100-point score is the sum of four capped components:

```text
queue score       = min(max queue / (capacity × 2), 1) × 30
wait score        = min(p90 wait / 60 minutes, 1) × 30
utilisation score = min(utilisation / 0.95, 1) × 25
duration score    = min(minutes above capacity / 120, 1) × 15
```

Ties are resolved deterministically by department name. Displayed component scores sum exactly to the displayed total.

## Live congestion

Live room status uses current queue pressure, longest current wait, capacity, and utilisation:

- normal: queue no larger than capacity, wait below 15 minutes, and utilisation below 75%;
- busy: pressure above 1, wait at least 15 minutes, or utilisation at least 75%;
- congested: pressure above 2, wait at least 30 minutes, or high utilisation with demand;
- critical: pressure above 3, wait at least 60 minutes, or near-saturated resources with a queue.

Operational findings are templates populated only from measured metrics. They are not AI recommendations. Real decisions require local thresholds, governed data, subject-matter review, and prospective validation.
