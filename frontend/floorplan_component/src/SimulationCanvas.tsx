import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import Konva from "konva";
import { Circle, Group, Layer, Line, Rect, RegularPolygon, Stage, Text } from "react-konva";
import type { KonvaEventObject } from "konva/lib/Node";
import { clamp, entityAtTime } from "./geometry";
import { TimelineControls } from "./TimelineControls";
import type { HospitalLayout, RenderedEntity, Timeline } from "./types";

interface Props {
  layout: HospitalLayout;
  timeline: Timeline;
  colours: Record<string, string>;
  highlight: string | null;
  time: number;
  playing: boolean;
  speed: number;
  onTime: (time: number) => void;
  onPlaying: (playing: boolean) => void;
  onSpeed: (speed: number) => void;
}

export function SimulationCanvas({ layout, timeline, colours, highlight, time, playing, speed, onTime, onPlaying, onSpeed }: Props) {
  const hostRef = useRef<HTMLDivElement>(null);
  const stageRef = useRef<Konva.Stage>(null);
  const lastTick = useRef<number | null>(null);
  const [size, setSize] = useState({ width: 940, height: 640 });
  const [zoom, setZoom] = useState(1);
  const [view, setView] = useState({ x: 20, y: 20 });
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [showMetrics, setShowMetrics] = useState(true);
  const pixelsPerMetre = Math.min((size.width - 40) / layout.canvas_width_m, (size.height - 40) / layout.canvas_height_m);

  useEffect(() => {
    if (!hostRef.current) return;
    const observer = new ResizeObserver(([entry]) => setSize({ width: Math.max(520, entry.contentRect.width), height: Math.max(520, entry.contentRect.height) }));
    observer.observe(hostRef.current); return () => observer.disconnect();
  }, []);

  useEffect(() => {
    if (!playing) { lastTick.current = null; return; }
    let request = 0;
    const tick = (now: number) => {
      const previous = lastTick.current ?? now;
      lastTick.current = now;
      const next = Math.min(timeline.duration, time + ((now - previous) / 1000) * speed);
      onTime(next);
      if (next >= timeline.duration) onPlaying(false); else request = requestAnimationFrame(tick);
    };
    request = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(request);
  }, [onPlaying, onTime, playing, speed, time, timeline.duration]);

  const patients = useMemo(() => timeline.patients.map((entity) => entityAtTime(entity, time)).filter((entity): entity is RenderedEntity => entity !== null), [time, timeline.patients]);
  const staff = useMemo(() => timeline.staff.map((entity) => entityAtTime(entity, time)).filter((entity): entity is RenderedEntity => entity !== null), [time, timeline.staff]);
  const occupied = useMemo(() => new Map(patients.filter((patient) => patient.seat_id).map((patient) => [patient.seat_id, patient.id])), [patients]);
  const selected = [...patients, ...staff].find((entity) => entity.id === selectedId);
  const eventTimes = useMemo(() => Array.from(new Set([...timeline.patients, ...timeline.staff].flatMap((entity) => entity.keyframes.map((frame) => frame.time)))).sort((a, b) => a - b), [timeline]);

  const fit = useCallback(() => {
    const next = Math.min((size.width - 40) / (layout.canvas_width_m * pixelsPerMetre), (size.height - 40) / (layout.canvas_height_m * pixelsPerMetre));
    setZoom(next); setView({ x: (size.width - layout.canvas_width_m * pixelsPerMetre * next) / 2, y: (size.height - layout.canvas_height_m * pixelsPerMetre * next) / 2 });
  }, [layout.canvas_height_m, layout.canvas_width_m, pixelsPerMetre, size]);

  const onWheel = (event: KonvaEventObject<WheelEvent>) => {
    event.evt.preventDefault(); const stage = stageRef.current; const pointer = stage?.getPointerPosition(); if (!pointer) return;
    const world = { x: (pointer.x - view.x) / zoom, y: (pointer.y - view.y) / zoom };
    const next = clamp(zoom * (event.evt.deltaY > 0 ? 0.9 : 1.1), 0.35, 4);
    setZoom(next); setView({ x: pointer.x - world.x * next, y: pointer.y - world.y * next });
  };

  const drawEntity = (entity: RenderedEntity) => {
    const x = entity.x_m * pixelsPerMetre; const y = entity.y_m * pixelsPerMetre; const radius = Math.max(5, pixelsPerMetre * 0.2);
    const dimmed = Boolean(highlight && entity.role === "patient" && entity.state !== highlight);
    const common = { opacity: dimmed ? 0.18 : 1, onClick: () => { onPlaying(false); setSelectedId(entity.id); }, onTap: () => { onPlaying(false); setSelectedId(entity.id); } };
    return <Group key={entity.id} x={x} y={y} {...common}>
      {entity.role === "patient" && <Circle radius={radius} fill={colours[entity.state] ?? "#64748b"} stroke={entity.border ?? "#334155"} strokeWidth={3 / zoom} />}
      {entity.role === "nurse" && <RegularPolygon sides={3} radius={radius * 1.15} fill="#22c55e" stroke="#14532d" strokeWidth={2 / zoom} />}
      {entity.role === "doctor" && <Rect x={-radius} y={-radius} width={radius * 2} height={radius * 2} fill="#1e3a8a" stroke="#0f172a" strokeWidth={2 / zoom} />}
      {entity.role === "patient" && entity.satisfaction_event && time - Number(entity.satisfaction_event.time) <= 2 && <Text x={radius + 3} y={radius + 2} text={`${Number(entity.satisfaction_event.score_change) > 0 ? "+" : ""}${entity.satisfaction_event.score_change} ${entity.satisfaction_event.event}`} fill="#b91c1c" fontSize={10 / zoom} />}
    </Group>;
  };

  const counts = patients.reduce<Record<string, number>>((result, patient) => ({ ...result, [patient.state]: (result[patient.state] ?? 0) + 1 }), {});
  const inside = patients.filter((patient) => patient.state !== "discharged");
  const availableSeats = layout.seats.filter((seat) => seat.available && !occupied.has(seat.id)).length;
  const averageSatisfaction = inside.length ? inside.reduce((total, patient) => total + Number(patient.satisfaction ?? 80), 0) / inside.length : 0;
  const doctorCapacity = timeline.resource_capacity?.doctors ?? staff.filter((entity) => entity.role === "doctor").length;
  const doctorBusy = (timeline.resource_intervals?.doctors ?? []).reduce((total, [start, end]) => total + (start < time ? Math.max(0, Math.min(time, end) - start) : 0), 0);
  const doctorUtilisation = doctorCapacity > 0 && time > 0 ? doctorBusy / (doctorCapacity * time) : 0;

  return <div className="simulation-shell">
    <div className="simulation-toolbar"><button onClick={fit}>Fit to screen</button><button onClick={() => { setZoom(1); setView({ x: 20, y: 20 }); }}>Reset view</button><label className="check"><input type="checkbox" checked={showMetrics} onChange={(event) => setShowMetrics(event.target.checked)} /> Metrics overlay</label></div>
    <TimelineControls playing={playing} time={time} duration={timeline.duration} speed={speed} eventTimes={eventTimes} onPlaying={onPlaying} onTime={onTime} onSpeed={onSpeed} />
    <div className="simulation-body"><div className="canvas-host" ref={hostRef}>
      <Stage ref={stageRef} width={size.width} height={size.height} x={view.x} y={view.y} scaleX={zoom} scaleY={zoom} draggable onDragEnd={(event) => { if (event.target === stageRef.current) setView({ x: event.target.x(), y: event.target.y() }); }} onWheel={onWheel} onMouseDown={(event) => { if (event.target === stageRef.current) setSelectedId(null); }}>
        <Layer>
          <Rect width={layout.canvas_width_m * pixelsPerMetre} height={layout.canvas_height_m * pixelsPerMetre} fill="#ffffff" stroke="#0f172a" strokeWidth={2 / zoom} />
          {layout.departments.map((department) => <Group key={department.id}><Rect x={department.x_m * pixelsPerMetre} y={department.y_m * pixelsPerMetre} width={department.width_m * pixelsPerMetre} height={department.height_m * pixelsPerMetre} fill={department.fill} stroke={department.border} strokeWidth={1.5 / zoom} /><Text x={(department.x_m + 0.15) * pixelsPerMetre} y={(department.y_m + 0.12) * pixelsPerMetre} text={department.name} fontSize={Math.max(8, pixelsPerMetre * 0.26)} fill="#0f172a" /></Group>)}
          {layout.queue_points.map((point) => <Line key={point.id} points={[point.x_m * pixelsPerMetre - 4, point.y_m * pixelsPerMetre, point.x_m * pixelsPerMetre + 4, point.y_m * pixelsPerMetre]} stroke="#64748b" dash={[2, 2]} />)}
          {layout.seats.map((seat) => <Rect key={seat.id} x={seat.x_m * pixelsPerMetre} y={seat.y_m * pixelsPerMetre} width={0.35 * pixelsPerMetre} height={0.35 * pixelsPerMetre} offsetX={0.175 * pixelsPerMetre} offsetY={0.175 * pixelsPerMetre} rotation={seat.rotation_deg} fill={!seat.available ? "#94a3b8" : occupied.has(seat.id) ? "#fb7185" : "#ffffff"} stroke="#475569" strokeWidth={1 / zoom} />)}
          {staff.map(drawEntity)}{patients.map(drawEntity)}
          {showMetrics && <Group x={10 / zoom} y={10 / zoom} scaleX={1 / zoom} scaleY={1 / zoom}><Rect width={720} height={32} fill="#ffffff" opacity={0.92} cornerRadius={6} stroke="#cbd5e1" /><Text x={10} y={9} text={`Time ${time.toFixed(1)} min · Inside ${inside.length} · Triage ${counts.waiting_triage ?? 0} · Initial ${counts.waiting_initial_consultation ?? 0} · Return ${counts.waiting_return_consultation ?? 0} · Seats ${availableSeats} · Satisfaction ${averageSatisfaction.toFixed(1)} · Doctors ${(doctorUtilisation * 100).toFixed(0)}%`} fontSize={12} fill="#0f172a" /></Group>}
        </Layer>
      </Stage>
    </div>
        <aside className="entity-panel"><h3>Selected person</h3>{!selected ? <p>Pause and select a patient, nurse, or doctor.</p> : <><h4>{selected.id}</h4><dl><dt>Role</dt><dd>{selected.role}</dd><dt>State</dt><dd>{selected.state}</dd><dt>Department</dt><dd>{String(selected.department_id ?? "—")}</dd>{selected.role === "patient" ? <><dt>Satisfaction</dt><dd>{Number(selected.satisfaction ?? 80).toFixed(0)}</dd><dt>Seat</dt><dd>{String(selected.seat_id ?? "—")}</dd><dt>Appointment</dt><dd>{String(selected.details?.appointment_time ?? "—")}</dd><dt>First wait</dt><dd>{Number(selected.details?.first_waiting_time ?? 0).toFixed(1)} min</dd><dt>Return wait</dt><dd>{Number(selected.details?.return_waiting_time ?? 0).toFixed(1)} min</dd><dt>Total wait</dt><dd>{Number(selected.details?.total_waiting_time ?? 0).toFixed(1)} min</dd><dt>Next destination</dt><dd>{String(selected.department_id ?? "—")}</dd></> : <><dt>Station</dt><dd>{String(selected.station_id ?? "—")}</dd><dt>Status</dt><dd>{selected.state}</dd><dt>Current patient</dt><dd>{String(selected.current_patient ?? "—")}</dd><dt>Utilisation so far</dt><dd>{(Number(selected.utilisation_so_far ?? 0) * 100).toFixed(1)}%</dd></>}</dl>{selected.role === "patient" && <details><summary>Satisfaction events</summary><pre>{JSON.stringify(selected.details?.satisfaction_events ?? [], null, 2)}</pre></details>}</>}</aside>
    </div>
  </div>;
}
