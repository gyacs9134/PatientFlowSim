import type { Department, HospitalLayout, ResourceStation, Seat } from "./types";

type Selection = { kind: "department"; value: Department } | { kind: "seat"; value: Seat } | { kind: "station"; value: ResourceStation } | null;

interface Props {
  selection: Selection;
  layout: HospitalLayout;
  onDepartment: (value: Department) => void;
  onSeat: (value: Seat) => void;
  onStation: (value: ResourceStation) => void;
  onDuplicate: () => void;
  onDelete: () => void;
}

const NumberField = ({ label, value, onChange, min = 0 }: { label: string; value: number; onChange: (value: number) => void; min?: number }) =>
  <label>{label}<input type="number" min={min} step="0.1" value={Number(value.toFixed(3))} onChange={(event) => onChange(Number(event.target.value))} /></label>;

export function PropertiesPanel({ selection, layout, onDepartment, onSeat, onStation, onDuplicate, onDelete }: Props) {
  if (!selection) return <aside className="properties-panel"><h3>Properties</h3><p>Select a room, seat, or resource station.</p></aside>;
  const actions = <div className="property-actions"><button onClick={onDuplicate}>Duplicate</button><button className="danger" onClick={onDelete}>Delete</button></div>;
  if (selection.kind === "department") {
    const value = selection.value;
    return <aside className="properties-panel"><h3>Department</h3>
      <label>Name<input value={value.name} onChange={(event) => onDepartment({ ...value, name: event.target.value })} /></label>
      <label>Type<select value={value.department_type} onChange={(event) => onDepartment({ ...value, department_type: event.target.value as Department["department_type"] })}>{["entrance", "check-in", "triage", "initial waiting area", "consultation room", "laboratory", "imaging", "return waiting area", "exit"].map((item) => <option key={item}>{item}</option>)}</select></label>
      <NumberField label="X (m)" value={value.x_m} onChange={(x_m) => onDepartment({ ...value, x_m: Math.min(x_m, layout.canvas_width_m - value.width_m) })} />
      <NumberField label="Y (m)" value={value.y_m} onChange={(y_m) => onDepartment({ ...value, y_m: Math.min(y_m, layout.canvas_height_m - value.height_m) })} />
      <NumberField label="Width (m)" min={0.1} value={value.width_m} onChange={(width_m) => onDepartment({ ...value, width_m: Math.max(0.1, Math.min(width_m, layout.canvas_width_m - value.x_m)) })} />
      <NumberField label="Height (m)" min={0.1} value={value.height_m} onChange={(height_m) => onDepartment({ ...value, height_m: Math.max(0.1, Math.min(height_m, layout.canvas_height_m - value.y_m)) })} />
      <label>Fill<input type="color" value={value.fill} onChange={(event) => onDepartment({ ...value, fill: event.target.value })} /></label>
      <label>Border<input type="color" value={value.border} onChange={(event) => onDepartment({ ...value, border: event.target.value })} /></label>{actions}</aside>;
  }
  if (selection.kind === "seat") {
    const value = selection.value;
    const waiting = layout.departments.filter((item) => item.department_type.includes("waiting area"));
    return <aside className="properties-panel"><h3>Seat</h3>
      <NumberField label="X (m)" value={value.x_m} onChange={(x_m) => onSeat({ ...value, x_m: Math.min(x_m, layout.canvas_width_m) })} />
      <NumberField label="Y (m)" value={value.y_m} onChange={(y_m) => onSeat({ ...value, y_m: Math.min(y_m, layout.canvas_height_m) })} />
      <NumberField label="Rotation (°)" min={-360} value={value.rotation_deg} onChange={(rotation_deg) => onSeat({ ...value, rotation_deg })} />
      <label>Waiting area<select value={value.waiting_area_id} onChange={(event) => onSeat({ ...value, waiting_area_id: event.target.value })}>{waiting.map((item) => <option value={item.id} key={item.id}>{item.name}</option>)}</select></label>
      <label className="check"><input type="checkbox" checked={value.available} onChange={(event) => onSeat({ ...value, available: event.target.checked })} /> Available</label>{actions}</aside>;
  }
  const value = selection.value;
  return <aside className="properties-panel"><h3>Resource station</h3>
    <label>Label<input value={value.label} onChange={(event) => onStation({ ...value, label: event.target.value })} /></label>
    <label>Type<select value={value.station_type} onChange={(event) => onStation({ ...value, station_type: event.target.value })}>{["check-in", "triage", "doctor", "laboratory", "imaging", "entry", "exit", "standing"].map((item) => <option key={item}>{item}</option>)}</select></label>
    <NumberField label="X (m)" value={value.x_m} onChange={(x_m) => onStation({ ...value, x_m: Math.min(x_m, layout.canvas_width_m) })} />
    <NumberField label="Y (m)" value={value.y_m} onChange={(y_m) => onStation({ ...value, y_m: Math.min(y_m, layout.canvas_height_m) })} />{actions}</aside>;
}

export type { Selection };
