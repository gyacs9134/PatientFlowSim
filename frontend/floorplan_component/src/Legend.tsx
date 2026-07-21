import type { RenderedEntity, Seat } from "./types";
import { stateCounts } from "./geometry";

const LABELS: Record<string, string> = {
  arrived_check_in: "Arrived / check-in",
  waiting_triage: "Waiting for triage",
  waiting_initial_consultation: "Waiting initial consultation",
  consultation: "In consultation",
  travelling_examination: "Travelling / waiting examination",
  examination: "Examination in progress",
  returning_examination: "Returning from examination",
  waiting_return_consultation: "Waiting return consultation",
  discharged: "Discharged / leaving",
};

interface Props {
  colours: Record<string, string>;
  entities?: RenderedEntity[];
  seats?: Seat[];
  collapsed: boolean;
  highlight: string | null;
  onToggle: () => void;
  onHighlight: (state: string | null) => void;
  onColour: (state: string, colour: string) => void;
  onRestore: () => void;
}

export function Legend({ colours, entities = [], seats = [], collapsed, highlight, onToggle, onHighlight, onColour, onRestore }: Props) {
  const counts = stateCounts(entities.filter((entity) => entity.role === "patient"));
  if (collapsed) return <button className="legend-toggle" onClick={onToggle}>Show legend</button>;
  return (
    <aside className="legend-panel" aria-label="Fixed floor-plan legend">
      <div className="panel-heading"><strong>Legend</strong><button onClick={onToggle}>Hide</button></div>
      <section><h4>Character shapes</h4><div>● Patient</div><div><span className="nurse-glyph">▲</span> Nurse</div><div><span className="doctor-glyph">■</span> Doctor</div></section>
      <section><h4>Patient states</h4>{Object.entries(LABELS).map(([state, label]) => (
        <div className={`legend-row ${highlight === state ? "active" : ""}`} key={state} onClick={() => onHighlight(highlight === state ? null : state)}>
          <input aria-label={`${label} colour`} type="color" value={colours[state] ?? "#64748b"} onClick={(event) => event.stopPropagation()} onChange={(event) => onColour(state, event.target.value)} />
          <span>{label}</span><b>{counts[state] ?? 0}</b>
        </div>
      ))}<button onClick={onRestore}>Restore colours</button></section>
      <section><h4>Satisfaction borders</h4><div><i className="border-swatch normal" /> 60–100</div><div><i className="border-swatch warning" /> 40–59</div><div><i className="border-swatch critical" /> 0–39</div></section>
      <section><h4>Seat states</h4><div>□ Empty ({seats.filter((seat) => seat.available && !seat.occupied).length})</div><div>▣ Occupied ({seats.filter((seat) => seat.occupied).length})</div><div>■ Unavailable ({seats.filter((seat) => !seat.available).length})</div></section>
    </aside>
  );
}
