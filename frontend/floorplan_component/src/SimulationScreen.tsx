import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Streamlit } from "streamlit-component-lib";
import { departmentPressures, queueSnapshots } from "./congestion";
import { EntityInspector } from "./EntityInspector";
import { entityAtTime } from "./geometry";
import { Legend } from "./Legend";
import { LiveMetrics } from "./LiveMetrics";
import { SimulationCanvas } from "./SimulationCanvas";
import { TimelineControls } from "./TimelineControls";
import type { HospitalLayout, OverlaySettings, RenderedEntity, Timeline } from "./types";

interface Props {
  layout: HospitalLayout;
  timeline: Timeline;
  initialColours: Record<string, string>;
  autoPlay: boolean;
  startTime: number;
  endTime: number;
  playbackSpeed: number;
  showFinish: boolean;
}

const DEFAULT_OVERLAYS: OverlaySettings = {
  congestion: true,
  queueLabels: true,
  flowTrails: false,
  seatOccupancy: true,
  averageWait: false,
  utilisation: false,
  satisfaction: false,
  patientIds: false,
};

export function SimulationScreen({ layout, timeline, initialColours, autoPlay, startTime, endTime, playbackSpeed, showFinish }: Props) {
  const safeEnd = Math.min(endTime || timeline.duration, timeline.duration);
  const [time, setTime] = useState(Math.min(startTime, safeEnd));
  const timeRef = useRef(time);
  const [playing, setPlaying] = useState(autoPlay);
  const [speed, setSpeed] = useState(playbackSpeed);
  const [colours, setColours] = useState(initialColours);
  const [legendCollapsed, setLegendCollapsed] = useState(false);
  const [highlight, setHighlight] = useState<string | null>(null);
  const [overlays, setOverlays] = useState(DEFAULT_OVERLAYS);
  const [overlayMenu, setOverlayMenu] = useState(false);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [fitSignal, setFitSignal] = useState(0);
  const completionSent = useRef(false);

  const changeTime = useCallback((value: number) => {
    const next = Math.max(startTime, Math.min(safeEnd, value));
    timeRef.current = next;
    setTime(next);
  }, [safeEnd, startTime]);

  useEffect(() => {
    if (!playing) return;
    let request = 0;
    let previous: number | null = null;
    const tick = (now: number) => {
      const elapsed = previous === null ? 0 : (now - previous) / 1000;
      previous = now;
      const next = Math.min(safeEnd, timeRef.current + elapsed * speed);
      changeTime(next);
      if (next >= safeEnd) {
        setPlaying(false);
        if (!completionSent.current) {
          completionSent.current = true;
          Streamlit.setComponentValue({ type: "simulation_complete", time: next });
        }
        return;
      }
      request = requestAnimationFrame(tick);
    };
    request = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(request);
  }, [changeTime, playing, safeEnd, speed]);

  const patients = useMemo(() => timeline.patients.map((entity) => entityAtTime(entity, time)).filter((entity): entity is RenderedEntity => entity !== null), [time, timeline.patients]);
  const staff = useMemo(() => timeline.staff.map((entity) => entityAtTime(entity, time)).filter((entity): entity is RenderedEntity => entity !== null), [time, timeline.staff]);
  const visible = useMemo(() => [...patients, ...staff], [patients, staff]);
  const renderedSeats = useMemo(() => {
    const occupied = new Set(patients.filter((entity) => entity.seat_id).map((entity) => String(entity.seat_id)));
    return layout.seats.map((seat) => ({ ...seat, occupied: occupied.has(seat.id), patient_id: occupied.has(seat.id) ? patients.find((patient) => patient.seat_id === seat.id)?.id ?? null : null }));
  }, [layout.seats, patients]);
  const occupiedSeatIds = useMemo(() => new Set(renderedSeats.filter((seat) => seat.occupied).map((seat) => seat.id)), [renderedSeats]);
  const queues = useMemo(() => queueSnapshots(patients, time, layout), [layout, patients, time]);
  const pressures = useMemo(() => departmentPressures(layout, queues, timeline, time), [layout, queues, time, timeline]);
  const selected = visible.find((entity) => entity.id === selectedId) ?? null;
  const eventTimes = useMemo(() => Array.from(new Set([...timeline.patients, ...timeline.staff].flatMap((entity) => entity.keyframes.map((frame) => frame.time)))).sort((a, b) => a - b), [timeline]);

  const finish = () => {
    setPlaying(false);
    changeTime(safeEnd);
    completionSent.current = true;
    Streamlit.setComponentValue({ type: "finish_simulation", time: safeEnd });
  };
  const toggleOverlay = (key: keyof OverlaySettings) => setOverlays((current) => ({ ...current, [key]: !current[key] }));

  return <div className="simulation-screen">
    <header className="simulation-topbar">
      <div className="simulation-brand"><i /> <div><strong>Clinic floor</strong><span>Patients move from the Python event timeline</span></div></div>
      <div className="topbar-actions">
        <button className={overlayMenu ? "active" : ""} onClick={() => setOverlayMenu((value) => !value)}>◫ Overlays</button>
        <button onClick={() => setFitSignal((value) => value + 1)}>⛶ Fit map</button>
      </div>
      {overlayMenu && <div className="overlay-menu">
        {(Object.keys(overlays) as (keyof OverlaySettings)[]).map((key) => <label key={key}><input type="checkbox" checked={overlays[key]} onChange={() => toggleOverlay(key)} /> {key.replaceAll(/([A-Z])/g, " $1").replaceAll("Ids", "IDs")}</label>)}
      </div>}
    </header>
    <div className="simulation-workspace">
      <div className="simulation-map-wrap">
        <SimulationCanvas layout={layout} patients={patients} staff={staff} queues={queues} pressures={pressures} colours={colours} highlight={highlight} overlays={overlays} selectedId={selectedId} fitSignal={fitSignal} time={time} onSelect={setSelectedId} onPause={() => setPlaying(false)} />
        {selected && <EntityInspector entity={selected} time={time} onClose={() => setSelectedId(null)} />}
      </div>
      <aside className="simulation-sidecar">
        <LiveMetrics entities={visible} layout={layout} timeline={timeline} time={time} occupiedSeatIds={occupiedSeatIds} />
        <Legend colours={colours} entities={visible} seats={renderedSeats} collapsed={legendCollapsed} highlight={highlight} onToggle={() => setLegendCollapsed((value) => !value)} onHighlight={setHighlight} onColour={(state, colour) => setColours((current) => ({ ...current, [state]: colour }))} onRestore={() => setColours(initialColours)} />
      </aside>
    </div>
    <TimelineControls playing={playing} time={time} startTime={startTime} endTime={safeEnd} speed={speed} eventTimes={eventTimes} showFinish={showFinish} onPlaying={setPlaying} onTime={changeTime} onSpeed={setSpeed} onFinish={finish} onFit={() => setFitSignal((value) => value + 1)} />
  </div>;
}
