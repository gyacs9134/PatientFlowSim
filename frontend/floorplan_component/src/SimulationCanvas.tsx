import { memo, useCallback, useEffect, useMemo, useRef, useState } from "react";
import Konva from "konva";
import { Circle, Group, Layer, Line, Rect, RegularPolygon, Stage, Text } from "react-konva";
import type { KonvaEventObject } from "konva/lib/Node";
import { CONGESTION_COLOURS } from "./congestion";
import { clamp } from "./geometry";
import type { DepartmentPressure, HospitalLayout, OverlaySettings, QueueSnapshot, RenderedEntity } from "./types";

interface Props {
  layout: HospitalLayout;
  patients: RenderedEntity[];
  staff: RenderedEntity[];
  queues: QueueSnapshot[];
  pressures: Record<string, DepartmentPressure>;
  colours: Record<string, string>;
  highlight: string | null;
  overlays: OverlaySettings;
  selectedId: string | null;
  fitSignal: number;
  time: number;
  onSelect: (id: string | null) => void;
  onPause: () => void;
}

interface StaticProps {
  layout: HospitalLayout;
  pixelsPerMetre: number;
  zoom: number;
  pressures: Record<string, DepartmentPressure>;
  queues: QueueSnapshot[];
  overlays: OverlaySettings;
  occupancy: Record<string, number>;
  satisfaction: Record<string, number>;
}

const StaticFloorPlan = memo(function StaticFloorPlan({ layout, pixelsPerMetre, zoom, pressures, queues, overlays, occupancy, satisfaction }: StaticProps) {
  return <>
    <Rect width={layout.canvas_width_m * pixelsPerMetre} height={layout.canvas_height_m * pixelsPerMetre} fill="#f8fafc" stroke="#334155" strokeWidth={2 / zoom} cornerRadius={4} />
    {layout.departments.map((department) => {
      const pressure = pressures[department.id];
      const border = overlays.congestion && pressure?.status !== "normal" ? CONGESTION_COLOURS[pressure.status] : department.border;
      const details = [
        overlays.seatOccupancy && occupancy[department.id] !== undefined ? `Occupancy ${occupancy[department.id]}` : "",
        overlays.averageWait && pressure?.longestWait ? `Longest wait ${pressure.longestWait.toFixed(0)}m` : "",
        overlays.utilisation && pressure?.utilisation ? `Util ${(pressure.utilisation * 100).toFixed(0)}%` : "",
        overlays.satisfaction && satisfaction[department.id] !== undefined ? `Sat ${satisfaction[department.id].toFixed(0)}` : "",
      ].filter(Boolean).join(" · ");
      return <Group key={department.id}>
        <Rect
          x={department.x_m * pixelsPerMetre} y={department.y_m * pixelsPerMetre}
          width={department.width_m * pixelsPerMetre} height={department.height_m * pixelsPerMetre}
          fill={department.fill} opacity={pressure?.status === "critical" && overlays.congestion ? .9 : 1}
          stroke={border} strokeWidth={(pressure?.status === "critical" && overlays.congestion ? 4 : 1.7) / zoom}
          shadowColor={pressure?.status === "critical" && overlays.congestion ? border : undefined}
          shadowBlur={pressure?.status === "critical" && overlays.congestion ? 8 / zoom : 0}
          cornerRadius={3 / zoom}
        />
        <Text x={(department.x_m + .16) * pixelsPerMetre} y={(department.y_m + .14) * pixelsPerMetre} width={(department.width_m - .3) * pixelsPerMetre} text={department.name} fontSize={Math.max(9, pixelsPerMetre * .25)} fontStyle="bold" fill="#172033" listening={false} />
        {details && <Text x={(department.x_m + .16) * pixelsPerMetre} y={(department.y_m + .58) * pixelsPerMetre} width={(department.width_m - .3) * pixelsPerMetre} text={details} fontSize={Math.max(7, pixelsPerMetre * .16)} fill="#526178" listening={false} />}
      </Group>;
    })}
    {layout.queue_points.map((point) => {
      const queue = queues.find((item) => item.queueType === point.point_type);
      if (!overlays.queueLabels || !queue || queue.queueLength === 0) return null;
      const text = `${queue.label}\nQueue ${queue.queueLength} · longest ${queue.longestWait.toFixed(0)} min`;
      const width = 4.2 * pixelsPerMetre;
      return <Group key={point.id} x={point.x_m * pixelsPerMetre} y={point.y_m * pixelsPerMetre}>
        <Line points={[-6 / zoom, 0, 6 / zoom, 0]} stroke="#475569" strokeWidth={2 / zoom} dash={[3 / zoom, 3 / zoom]} />
        <Rect x={8 / zoom} y={-18 / zoom} width={width} height={34 / zoom} fill="#ffffff" opacity={.94} stroke="#cbd5e1" strokeWidth={1 / zoom} cornerRadius={5 / zoom} />
        <Text x={13 / zoom} y={-14 / zoom} width={width - 10 / zoom} text={text} fontSize={9 / zoom} lineHeight={1.2} fill="#263247" />
      </Group>;
    })}
  </>;
});

export function SimulationCanvas({ layout, patients, staff, queues, pressures, colours, highlight, overlays, selectedId, fitSignal, time, onSelect, onPause }: Props) {
  const hostRef = useRef<HTMLDivElement>(null);
  const stageRef = useRef<Konva.Stage>(null);
  const [size, setSize] = useState({ width: 980, height: 640 });
  const [zoom, setZoom] = useState(1);
  const [view, setView] = useState({ x: 16, y: 16 });
  const pixelsPerMetre = Math.min((size.width - 32) / layout.canvas_width_m, (size.height - 32) / layout.canvas_height_m);

  useEffect(() => {
    if (!hostRef.current) return;
    const observer = new ResizeObserver(([entry]) => setSize({ width: Math.max(560, entry.contentRect.width), height: Math.max(540, entry.contentRect.height) }));
    observer.observe(hostRef.current);
    return () => observer.disconnect();
  }, []);

  const fit = useCallback(() => {
    setZoom(1);
    setView({ x: (size.width - layout.canvas_width_m * pixelsPerMetre) / 2, y: (size.height - layout.canvas_height_m * pixelsPerMetre) / 2 });
  }, [layout.canvas_height_m, layout.canvas_width_m, pixelsPerMetre, size]);
  useEffect(() => { fit(); }, [fit, fitSignal]);

  const onWheel = (event: KonvaEventObject<WheelEvent>) => {
    event.evt.preventDefault();
    const pointer = stageRef.current?.getPointerPosition();
    if (!pointer) return;
    const world = { x: (pointer.x - view.x) / zoom, y: (pointer.y - view.y) / zoom };
    const next = clamp(zoom * (event.evt.deltaY > 0 ? .9 : 1.1), .35, 4);
    setZoom(next);
    setView({ x: pointer.x - world.x * next, y: pointer.y - world.y * next });
  };

  const occupied = useMemo(() => new Map(patients.filter((patient) => patient.seat_id).map((patient) => [String(patient.seat_id), patient.id])), [patients]);
  const occupancy = useMemo(() => [...patients.filter((entity) => entity.state !== "discharged"), ...staff].reduce<Record<string, number>>((counts, entity) => {
    if (entity.department_id) counts[String(entity.department_id)] = (counts[String(entity.department_id)] ?? 0) + 1;
    return counts;
  }, {}), [patients, staff]);
  const satisfaction = useMemo(() => {
    const totals: Record<string, { total: number; count: number }> = {};
    patients.forEach((patient) => {
      if (!patient.department_id) return;
      const key = String(patient.department_id);
      const current = totals[key] ?? { total: 0, count: 0 };
      totals[key] = { total: current.total + Number(patient.satisfaction ?? 80), count: current.count + 1 };
    });
    return Object.fromEntries(Object.entries(totals).map(([key, item]) => [key, item.total / item.count]));
  }, [patients]);

  const select = (id: string) => { onPause(); onSelect(id); };
  const drawEntity = (entity: RenderedEntity) => {
    const x = entity.x_m * pixelsPerMetre;
    const y = entity.y_m * pixelsPerMetre;
    const radius = Math.max(5, Math.min(9, pixelsPerMetre * .2));
    const dimmed = Boolean(highlight && entity.role === "patient" && entity.state !== highlight);
    const active = selectedId === entity.id;
    return <Group key={entity.id} x={x} y={y} opacity={dimmed ? .14 : 1} onClick={() => select(entity.id)} onTap={() => select(entity.id)}>
      {entity.role === "patient" && <Circle radius={radius} fill={colours[entity.state] ?? "#64748b"} stroke={active ? "#0ea5e9" : entity.border ?? "#334155"} strokeWidth={(active ? 4 : 3) / zoom} shadowColor={active ? "#0ea5e9" : undefined} shadowBlur={active ? 8 / zoom : 0} />}
      {entity.role === "nurse" && <RegularPolygon sides={3} radius={radius * 1.18} fill="#22c55e" stroke={active ? "#0ea5e9" : "#14532d"} strokeWidth={(active ? 4 : 2) / zoom} />}
      {entity.role === "doctor" && <Rect x={-radius} y={-radius} width={radius * 2} height={radius * 2} fill="#1e3a8a" stroke={active ? "#0ea5e9" : "#0f172a"} strokeWidth={(active ? 4 : 2) / zoom} cornerRadius={1.5 / zoom} />}
      {overlays.patientIds && entity.role === "patient" && <Text x={radius + 2 / zoom} y={-radius} text={entity.id} fontSize={8 / zoom} fill="#172033" />}
      {entity.role === "patient" && entity.satisfaction_event && time - Number(entity.satisfaction_event.time) <= 2 && <Text x={radius + 3 / zoom} y={radius + 2 / zoom} text={`${Number(entity.satisfaction_event.score_change) > 0 ? "+" : ""}${entity.satisfaction_event.score_change} ${String(entity.satisfaction_event.event).replaceAll("_", " ")}`} fill="#b91c1c" fontSize={9 / zoom} />}
    </Group>;
  };

  return <div className="simulation-map" ref={hostRef}>
    <Stage ref={stageRef} width={size.width} height={size.height} x={view.x} y={view.y} scaleX={zoom} scaleY={zoom} draggable
      onDragEnd={(event) => { if (event.target === stageRef.current) setView({ x: event.target.x(), y: event.target.y() }); }}
      onWheel={onWheel} onMouseDown={(event) => { if (event.target === stageRef.current) onSelect(null); }}>
      <Layer listening={false}>
        <StaticFloorPlan layout={layout} pixelsPerMetre={pixelsPerMetre} zoom={zoom} pressures={pressures} queues={queues} overlays={overlays} occupancy={occupancy} satisfaction={satisfaction} />
        {layout.seats.map((seat) => <Rect key={seat.id} x={seat.x_m * pixelsPerMetre} y={seat.y_m * pixelsPerMetre} width={.36 * pixelsPerMetre} height={.36 * pixelsPerMetre} offsetX={.18 * pixelsPerMetre} offsetY={.18 * pixelsPerMetre} rotation={seat.rotation_deg} fill={!seat.available ? "#94a3b8" : occupied.has(seat.id) ? "#fb7185" : "#ffffff"} stroke="#475569" strokeWidth={1.2 / zoom} cornerRadius={2 / zoom} />)}
      </Layer>
      <Layer>
        {overlays.flowTrails && patients.filter((patient) => patient.moving && patient.source_location).map((patient) => <Line key={`trail_${patient.id}`} points={[Number(patient.source_location?.x_m) * pixelsPerMetre, Number(patient.source_location?.y_m) * pixelsPerMetre, patient.x_m * pixelsPerMetre, patient.y_m * pixelsPerMetre]} stroke={colours[patient.state] ?? "#64748b"} opacity={.35} strokeWidth={3 / zoom} lineCap="round" dash={[5 / zoom, 4 / zoom]} />)}
        {staff.map(drawEntity)}
        {patients.map(drawEntity)}
      </Layer>
    </Stage>
  </div>;
}
