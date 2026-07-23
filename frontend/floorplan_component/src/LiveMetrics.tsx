import { resourceUtilisation } from "./congestion";
import type { HospitalLayout, RenderedEntity, Timeline } from "./types";

interface Props { entities: RenderedEntity[]; layout: HospitalLayout; timeline: Timeline; time: number; occupiedSeatIds: Set<string>; }

const metric = (label: string, value: string | number) => <div className="live-metric"><span>{label}</span><strong>{value}</strong></div>;

export function LiveMetrics({ entities, layout, timeline, time, occupiedSeatIds }: Props) {
  const patients = entities.filter((entity) => entity.role === "patient");
  const inside = patients.filter((patient) => patient.state !== "discharged");
  const count = (state: string) => patients.filter((patient) => patient.state === state).length;
  const availableSeats = layout.seats.filter((seat) => seat.available && !occupiedSeatIds.has(seat.id)).length;
  const satisfaction = inside.length ? inside.reduce((sum, patient) => sum + Number(patient.satisfaction ?? 80), 0) / inside.length : 0;
  return <section className="live-metrics" aria-label="Live clinic metrics">
    <div className="side-heading"><span>Live clinic</span><i>updated locally</i></div>
    <div className="metric-grid">
      {metric("Inside clinic", inside.length)}
      {metric("Waiting triage", count("waiting_triage"))}
      {metric("Initial queue", count("waiting_initial_consultation"))}
      {metric("Return queue", count("waiting_return_consultation"))}
      {metric("Available seats", availableSeats)}
      {metric("Avg. satisfaction", satisfaction.toFixed(1))}
      {metric("Doctor utilisation", `${(resourceUtilisation("doctors", time, timeline) * 100).toFixed(0)}%`)}
      {metric("Returning", count("returning_examination"))}
    </div>
  </section>;
}
