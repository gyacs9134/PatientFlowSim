import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import Konva from "konva";
import { Circle, Group, Layer, Line, Rect, Stage, Text, Transformer } from "react-konva";
import type { KonvaEventObject } from "konva/lib/Node";
import type { Department, HospitalLayout, ResourceStation, Seat } from "./types";
import { clamp, overlapWarnings, snap } from "./geometry";
import { PropertiesPanel, type Selection } from "./PropertiesPanel";

interface Props {
  layout: HospitalLayout;
  onChange: (layout: HospitalLayout) => void;
  onCommit: (layout: HospitalLayout) => void;
  onUndo: () => void;
  onRedo: () => void;
  canUndo: boolean;
  canRedo: boolean;
}

const uniqueId = (prefix: string) => `${prefix}_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 6)}`;

export function EditorCanvas({ layout, onChange, onCommit, onUndo, onRedo, canUndo, canRedo }: Props) {
  const hostRef = useRef<HTMLDivElement>(null);
  const stageRef = useRef<Konva.Stage>(null);
  const transformerRef = useRef<Konva.Transformer>(null);
  const [size, setSize] = useState({ width: 860, height: 650 });
  const [zoom, setZoom] = useState(1);
  const [view, setView] = useState({ x: 20, y: 20 });
  const [snapEnabled, setSnapEnabled] = useState(true);
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [seatRows, setSeatRows] = useState(2);
  const [seatColumns, setSeatColumns] = useState(5);
  const [rowSpacing, setRowSpacing] = useState(0.7);
  const [columnSpacing, setColumnSpacing] = useState(0.7);
  const pixelsPerMetre = Math.min((size.width - 40) / layout.canvas_width_m, (size.height - 40) / layout.canvas_height_m);

  useEffect(() => {
    if (!hostRef.current) return;
    const observer = new ResizeObserver(([entry]) => setSize({ width: Math.max(480, entry.contentRect.width), height: Math.max(520, entry.contentRect.height) }));
    observer.observe(hostRef.current);
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    const stage = stageRef.current;
    const transformer = transformerRef.current;
    if (!stage || !transformer) return;
    transformer.nodes(selectedIds.map((id) => stage.findOne(`#${id}`)).filter((node): node is Konva.Node => Boolean(node)));
    transformer.getLayer()?.batchDraw();
  }, [selectedIds, layout]);

  const selected: Selection = useMemo(() => {
    const id = selectedIds[0];
    const department = layout.departments.find((item) => item.id === id);
    if (department) return { kind: "department", value: department };
    const seat = layout.seats.find((item) => item.id === id);
    if (seat) return { kind: "seat", value: seat };
    const station = layout.resource_stations.find((item) => item.id === id);
    return station ? { kind: "station", value: station } : null;
  }, [layout, selectedIds]);

  const choose = (id: string, event: KonvaEventObject<Event>) => {
    event.cancelBubble = true;
    const multi = "shiftKey" in event.evt && Boolean((event.evt as MouseEvent).shiftKey);
    setSelectedIds((current) => multi ? (current.includes(id) ? current.filter((item) => item !== id) : [...current, id]) : [id]);
  };

  const fit = useCallback(() => {
    const scale = Math.min((size.width - 40) / (layout.canvas_width_m * pixelsPerMetre), (size.height - 40) / (layout.canvas_height_m * pixelsPerMetre));
    setZoom(scale);
    setView({ x: (size.width - layout.canvas_width_m * pixelsPerMetre * scale) / 2, y: (size.height - layout.canvas_height_m * pixelsPerMetre * scale) / 2 });
  }, [layout.canvas_height_m, layout.canvas_width_m, pixelsPerMetre, size]);

  const updateDepartment = (department: Department, commit = true) => {
    const next = { ...layout, departments: layout.departments.map((item) => item.id === department.id ? department : item) };
    onChange(next);
    if (commit) onCommit(next);
  };
  const updateSeat = (seat: Seat, commit = true) => {
    const next = { ...layout, seats: layout.seats.map((item) => item.id === seat.id ? seat : item) };
    onChange(next);
    if (commit) onCommit(next);
  };
  const updateStation = (station: ResourceStation, commit = true) => {
    const next = { ...layout, resource_stations: layout.resource_stations.map((item) => item.id === station.id ? station : item) };
    onChange(next);
    if (commit) onCommit(next);
  };

  const removeSelected = useCallback(() => {
    if (!selectedIds.length) return;
    const ids = new Set(selectedIds);
    const next = {
      ...layout,
      departments: layout.departments.filter((item) => !ids.has(item.id)),
      seats: layout.seats.filter((item) => !ids.has(item.id)),
      resource_stations: layout.resource_stations.filter((item) => !ids.has(item.id)),
    };
    setSelectedIds([]);
    onCommit(next);
  }, [layout, onCommit, selectedIds]);

  useEffect(() => {
    const handler = (event: KeyboardEvent) => {
      if ((event.key === "Delete" || event.key === "Backspace") && !(event.target instanceof HTMLInputElement) && !(event.target instanceof HTMLSelectElement)) removeSelected();
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "z") event.shiftKey ? onRedo() : onUndo();
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [onRedo, onUndo, removeSelected]);

  const addDepartment = () => {
    const id = uniqueId("department");
    const department: Department = { id, name: "New department", department_type: "consultation room", x_m: 1, y_m: 1, width_m: 4, height_m: 3, fill: "#dbeafe", border: "#475569" };
    onCommit({ ...layout, departments: [...layout.departments, department] }); setSelectedIds([id]);
  };
  const addSeat = () => {
    const waiting = layout.departments.find((item) => item.department_type.includes("waiting area"));
    if (!waiting) return;
    const id = uniqueId("seat");
    const seat: Seat = { id, x_m: waiting.x_m + 0.5, y_m: waiting.y_m + 0.5, rotation_deg: 0, waiting_area_id: waiting.id, available: true, occupied: false, patient_id: null };
    onCommit({ ...layout, seats: [...layout.seats, seat] }); setSelectedIds([id]);
  };
  const generateSeats = () => {
    const waiting = layout.departments.find((item) => item.id === (selected?.kind === "department" ? selected.value.id : "") && item.department_type.includes("waiting area")) ?? layout.departments.find((item) => item.department_type.includes("waiting area"));
    if (!waiting) return;
    const seats: Seat[] = [];
    for (let row = 0; row < seatRows; row += 1) for (let column = 0; column < seatColumns; column += 1) {
      seats.push({ id: uniqueId("seat"), x_m: clamp(waiting.x_m + 0.5 + column * columnSpacing, 0, layout.canvas_width_m), y_m: clamp(waiting.y_m + 0.5 + row * rowSpacing, 0, layout.canvas_height_m), rotation_deg: 0, waiting_area_id: waiting.id, available: true, occupied: false, patient_id: null });
    }
    onCommit({ ...layout, seats: [...layout.seats, ...seats] });
  };
  const addStation = () => {
    const id = uniqueId("station");
    const station: ResourceStation = { id, station_type: "doctor", x_m: 2, y_m: 2, department_id: null, resource_index: layout.resource_stations.length, label: "Station" };
    onCommit({ ...layout, resource_stations: [...layout.resource_stations, station] }); setSelectedIds([id]);
  };

  const duplicateSelected = () => {
    if (!selected) return;
    if (selected.kind === "department") {
      const copy = { ...selected.value, id: uniqueId("department"), name: `${selected.value.name} copy`, x_m: clamp(selected.value.x_m + 0.5, 0, layout.canvas_width_m - selected.value.width_m), y_m: clamp(selected.value.y_m + 0.5, 0, layout.canvas_height_m - selected.value.height_m) };
      onCommit({ ...layout, departments: [...layout.departments, copy] }); setSelectedIds([copy.id]);
    } else if (selected.kind === "seat") {
      const copy = { ...selected.value, id: uniqueId("seat"), x_m: clamp(selected.value.x_m + 0.4, 0, layout.canvas_width_m), y_m: clamp(selected.value.y_m + 0.4, 0, layout.canvas_height_m), occupied: false, patient_id: null };
      onCommit({ ...layout, seats: [...layout.seats, copy] }); setSelectedIds([copy.id]);
    } else {
      const copy = { ...selected.value, id: uniqueId("station"), x_m: clamp(selected.value.x_m + 0.4, 0, layout.canvas_width_m), y_m: clamp(selected.value.y_m + 0.4, 0, layout.canvas_height_m) };
      onCommit({ ...layout, resource_stations: [...layout.resource_stations, copy] }); setSelectedIds([copy.id]);
    }
  };

  const onWheel = (event: KonvaEventObject<WheelEvent>) => {
    event.evt.preventDefault();
    const stage = stageRef.current;
    if (!stage) return;
    const pointer = stage.getPointerPosition();
    if (!pointer) return;
    const oldZoom = zoom;
    const world = { x: (pointer.x - view.x) / oldZoom, y: (pointer.y - view.y) / oldZoom };
    const nextZoom = clamp(oldZoom * (event.evt.deltaY > 0 ? 0.9 : 1.1), 0.35, 4);
    setZoom(nextZoom);
    setView({ x: pointer.x - world.x * nextZoom, y: pointer.y - world.y * nextZoom });
  };

  const warnings = overlapWarnings(layout);
  const grid: React.ReactNode[] = [];
  for (let x = 0; x <= layout.canvas_width_m + 0.001; x += layout.grid_spacing_m) grid.push(<Line key={`x${x}`} points={[x * pixelsPerMetre, 0, x * pixelsPerMetre, layout.canvas_height_m * pixelsPerMetre]} stroke="#e2e8f0" strokeWidth={1 / zoom} listening={false} />);
  for (let y = 0; y <= layout.canvas_height_m + 0.001; y += layout.grid_spacing_m) grid.push(<Line key={`y${y}`} points={[0, y * pixelsPerMetre, layout.canvas_width_m * pixelsPerMetre, y * pixelsPerMetre]} stroke="#e2e8f0" strokeWidth={1 / zoom} listening={false} />);

  return <div className="editor-shell">
    <div className="editor-main">
      <div className="editor-toolbar">
        <button onClick={addDepartment}>+ Department</button><button onClick={addSeat}>+ Seat</button><button onClick={addStation}>+ Station</button>
        <span className="divider" /><button disabled={!canUndo} onClick={onUndo}>Undo</button><button disabled={!canRedo} onClick={onRedo}>Redo</button>
        <button onClick={fit}>Fit</button><button onClick={() => { setZoom(1); setView({ x: 20, y: 20 }); }}>Reset view</button>
        <button onClick={() => setView({ x: (size.width - layout.canvas_width_m * pixelsPerMetre * zoom) / 2, y: (size.height - layout.canvas_height_m * pixelsPerMetre * zoom) / 2 })}>Centre</button>
        <label className="check"><input type="checkbox" checked={snapEnabled} onChange={(event) => setSnapEnabled(event.target.checked)} /> Snap</label>
        <select value={layout.grid_spacing_m} onChange={(event) => onCommit({ ...layout, grid_spacing_m: Number(event.target.value) as HospitalLayout["grid_spacing_m"] })}><option value={0.25}>0.25 m</option><option value={0.5}>0.5 m</option><option value={1}>1 m</option></select>
      </div>
      <div className="seat-generator"><span>Seat grid</span><label>Rows <input type="number" min={1} max={20} value={seatRows} onChange={(event) => setSeatRows(Number(event.target.value))} /></label><label>Columns <input type="number" min={1} max={20} value={seatColumns} onChange={(event) => setSeatColumns(Number(event.target.value))} /></label><label>Row m <input type="number" min={0.2} step={0.1} value={rowSpacing} onChange={(event) => setRowSpacing(Number(event.target.value))} /></label><label>Column m <input type="number" min={0.2} step={0.1} value={columnSpacing} onChange={(event) => setColumnSpacing(Number(event.target.value))} /></label><button onClick={generateSeats}>Generate</button></div>
      {warnings.length > 0 && <div className="warning-strip">⚠ {warnings.slice(0, 3).join("; ")}{warnings.length > 3 ? ` (+${warnings.length - 3})` : ""}</div>}
      <div className="canvas-host" ref={hostRef}>
        <Stage ref={stageRef} width={size.width} height={size.height} x={view.x} y={view.y} scaleX={zoom} scaleY={zoom} draggable onDragEnd={(event) => { if (event.target === stageRef.current) setView({ x: event.target.x(), y: event.target.y() }); }} onWheel={onWheel} onMouseDown={(event) => { if (event.target === stageRef.current) setSelectedIds([]); }}>
          <Layer>
            <Rect width={layout.canvas_width_m * pixelsPerMetre} height={layout.canvas_height_m * pixelsPerMetre} fill="#ffffff" stroke="#0f172a" strokeWidth={2 / zoom} />
            {grid}
            {layout.departments.map((department) => <Group key={department.id}>
              <Rect id={department.id} x={department.x_m * pixelsPerMetre} y={department.y_m * pixelsPerMetre} width={department.width_m * pixelsPerMetre} height={department.height_m * pixelsPerMetre} fill={department.fill} stroke={selectedIds.includes(department.id) ? "#2563eb" : department.border} strokeWidth={(selectedIds.includes(department.id) ? 3 : 1.5) / zoom} draggable onClick={(event) => choose(department.id, event)} onTap={(event) => choose(department.id, event)} onDragMove={(event) => {
                const x_m = clamp(snap(event.target.x() / pixelsPerMetre, layout.grid_spacing_m, snapEnabled), 0, layout.canvas_width_m - department.width_m);
                const y_m = clamp(snap(event.target.y() / pixelsPerMetre, layout.grid_spacing_m, snapEnabled), 0, layout.canvas_height_m - department.height_m);
                event.target.position({ x: x_m * pixelsPerMetre, y: y_m * pixelsPerMetre }); updateDepartment({ ...department, x_m, y_m }, false);
              }} onDragEnd={(event) => updateDepartment({ ...department, x_m: event.target.x() / pixelsPerMetre, y_m: event.target.y() / pixelsPerMetre })} onTransformEnd={(event) => {
                const node = event.target; const width_m = Math.max(0.1, node.width() * node.scaleX() / pixelsPerMetre); const height_m = Math.max(0.1, node.height() * node.scaleY() / pixelsPerMetre); node.scale({ x: 1, y: 1 });
                const next = { ...department, x_m: clamp(node.x() / pixelsPerMetre, 0, layout.canvas_width_m - width_m), y_m: clamp(node.y() / pixelsPerMetre, 0, layout.canvas_height_m - height_m), width_m: Math.min(width_m, layout.canvas_width_m - node.x() / pixelsPerMetre), height_m: Math.min(height_m, layout.canvas_height_m - node.y() / pixelsPerMetre) }; updateDepartment(next);
              }} />
              <Text x={(department.x_m + 0.15) * pixelsPerMetre} y={(department.y_m + 0.12) * pixelsPerMetre} text={department.name} fontSize={Math.max(8, pixelsPerMetre * 0.28)} fill="#0f172a" listening={false} />
              {selectedIds.includes(department.id) && <Text x={department.x_m * pixelsPerMetre} y={(department.y_m + department.height_m) * pixelsPerMetre + 3} text={`Width ${department.width_m.toFixed(2)} m · Height ${department.height_m.toFixed(2)} m · X ${department.x_m.toFixed(2)} · Y ${department.y_m.toFixed(2)}`} fontSize={11 / zoom} fill="#1d4ed8" listening={false} />}
            </Group>)}
            {layout.seats.map((seat) => <Rect id={seat.id} key={seat.id} x={seat.x_m * pixelsPerMetre} y={seat.y_m * pixelsPerMetre} width={0.35 * pixelsPerMetre} height={0.35 * pixelsPerMetre} offsetX={0.175 * pixelsPerMetre} offsetY={0.175 * pixelsPerMetre} rotation={seat.rotation_deg} fill={seat.available ? "#ffffff" : "#94a3b8"} stroke={selectedIds.includes(seat.id) ? "#2563eb" : "#475569"} strokeWidth={2 / zoom} draggable onClick={(event) => choose(seat.id, event)} onDragMove={(event) => updateSeat({ ...seat, x_m: clamp(snap(event.target.x() / pixelsPerMetre, layout.grid_spacing_m, snapEnabled), 0, layout.canvas_width_m), y_m: clamp(snap(event.target.y() / pixelsPerMetre, layout.grid_spacing_m, snapEnabled), 0, layout.canvas_height_m) }, false)} onDragEnd={(event) => updateSeat({ ...seat, x_m: event.target.x() / pixelsPerMetre, y_m: event.target.y() / pixelsPerMetre })} />)}
            {layout.resource_stations.map((station) => <Group id={station.id} key={station.id} x={station.x_m * pixelsPerMetre} y={station.y_m * pixelsPerMetre} draggable onClick={(event) => choose(station.id, event)} onDragMove={(event) => updateStation({ ...station, x_m: clamp(snap(event.target.x() / pixelsPerMetre, layout.grid_spacing_m, snapEnabled), 0, layout.canvas_width_m), y_m: clamp(snap(event.target.y() / pixelsPerMetre, layout.grid_spacing_m, snapEnabled), 0, layout.canvas_height_m) }, false)} onDragEnd={(event) => updateStation({ ...station, x_m: event.target.x() / pixelsPerMetre, y_m: event.target.y() / pixelsPerMetre })}><Circle radius={0.22 * pixelsPerMetre} fill="#0f766e" stroke={selectedIds.includes(station.id) ? "#2563eb" : "#134e4a"} strokeWidth={2 / zoom} /><Text text={station.label || station.station_type} x={0.28 * pixelsPerMetre} y={-0.15 * pixelsPerMetre} fontSize={10 / zoom} /></Group>)}
            <Transformer ref={transformerRef} rotateEnabled={false} keepRatio={false} flipEnabled={false} boundBoxFunc={(oldBox, newBox) => newBox.width < pixelsPerMetre * 0.1 || newBox.height < pixelsPerMetre * 0.1 ? oldBox : newBox} />
          </Layer>
        </Stage>
      </div>
    </div>
    <PropertiesPanel selection={selected} layout={layout} onDepartment={updateDepartment} onSeat={updateSeat} onStation={updateStation} onDuplicate={duplicateSelected} onDelete={removeSelected} />
  </div>;
}
