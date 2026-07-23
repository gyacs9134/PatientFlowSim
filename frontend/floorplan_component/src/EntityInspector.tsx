import { nextKeyframe } from "./geometry";
import type { RenderedEntity } from "./types";

interface Props { entity: RenderedEntity; time: number; onClose: () => void; }

const value = (candidate: unknown) => candidate === null || candidate === undefined || candidate === "" ? "—" : String(candidate);

export function EntityInspector({ entity, time, onClose }: Props) {
  const next = nextKeyframe(entity, time);
  return <aside className="entity-inspector">
    <div className="inspector-heading"><div><small>{entity.role}</small><strong>{entity.id}</strong></div><button aria-label="Close inspector" onClick={onClose}>×</button></div>
    <dl>
      <dt>Current state</dt><dd>{entity.state.replaceAll("_", " ")}</dd>
      <dt>Department</dt><dd>{value(entity.department_id)}</dd>
      <dt>Next destination</dt><dd>{value(next?.department_id)}</dd>
      {entity.role === "patient" ? <>
        <dt>Appointment</dt><dd>{Number(entity.details?.appointment_time ?? 0).toFixed(1)} min</dd>
        <dt>Waiting now</dt><dd>{entity.queue_entered_time === null || entity.queue_entered_time === undefined ? "—" : `${Math.max(0, time - Number(entity.queue_entered_time)).toFixed(1)} min`}</dd>
        <dt>Total waiting</dt><dd>{Number(entity.details?.total_waiting_time ?? 0).toFixed(1)} min</dd>
        <dt>Satisfaction</dt><dd>{Number(entity.satisfaction ?? 80).toFixed(0)} / 100</dd>
        <dt>Seat</dt><dd>{value(entity.seat_id)}</dd>
        <dt>Examination</dt><dd>{value(entity.details?.examination_type)}</dd>
      </> : <>
        <dt>Station</dt><dd>{value(entity.station_id)}</dd>
        <dt>Current patient</dt><dd>{value(entity.current_patient)}</dd>
        <dt>Utilisation</dt><dd>{(Number(entity.utilisation_so_far ?? 0) * 100).toFixed(1)}%</dd>
      </>}
    </dl>
    {entity.role === "patient" && <details><summary>Satisfaction events</summary><pre>{JSON.stringify(entity.details?.satisfaction_events ?? [], null, 2)}</pre></details>}
  </aside>;
}
