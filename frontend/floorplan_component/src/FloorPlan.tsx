import { useEffect, useMemo, useRef, useState } from "react";
import { Streamlit } from "streamlit-component-lib";
import { EditorCanvas } from "./EditorCanvas";
import { Legend } from "./Legend";
import { SimulationCanvas } from "./SimulationCanvas";
import { entityAtTime } from "./geometry";
import type { ComponentArgs, HospitalLayout, RenderedEntity } from "./types";

const DEFAULT_COLOURS: Record<string, string> = {
  arrived_check_in: "#2563eb", waiting_triage: "#eab308", waiting_initial_consultation: "#f97316", consultation: "#7c3aed",
  travelling_examination: "#06b6d4", examination: "#0e7490", returning_examination: "#ef4444", waiting_return_consultation: "#991b1b", discharged: "#64748b",
};

export function FloorPlan({ layout: initialLayout, timeline, mode, height }: ComponentArgs) {
  const [layout, setLayout] = useState<HospitalLayout>(initialLayout);
  const [history, setHistory] = useState<HospitalLayout[]>([initialLayout]);
  const [historyIndex, setHistoryIndex] = useState(0);
  const [legendCollapsed, setLegendCollapsed] = useState(false);
  const [highlight, setHighlight] = useState<string | null>(null);
  const [time, setTime] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [speed, setSpeed] = useState(1);
  const lastPythonLayout = useRef(JSON.stringify(initialLayout));

  useEffect(() => {
    const incoming = JSON.stringify(initialLayout);
    if (incoming !== lastPythonLayout.current) {
      lastPythonLayout.current = incoming; setLayout(initialLayout); setHistory([initialLayout]); setHistoryIndex(0);
    }
  }, [initialLayout]);
  useEffect(() => { Streamlit.setFrameHeight(height); }, [height, layout, mode]);

  const commit = (next: HospitalLayout) => {
    setLayout(next);
    const branch = history.slice(0, historyIndex + 1);
    const nextHistory = [...branch, next].slice(-50);
    setHistory(nextHistory); setHistoryIndex(nextHistory.length - 1);
    lastPythonLayout.current = JSON.stringify(next);
    Streamlit.setComponentValue({ type: "layout_changed", layout: next });
  };
  const publishHistory = (index: number) => {
    const next = history[index];
    setHistoryIndex(index); setLayout(next); lastPythonLayout.current = JSON.stringify(next);
    Streamlit.setComponentValue({ type: "layout_changed", layout: next });
  };
  const undo = () => { if (historyIndex > 0) publishHistory(historyIndex - 1); };
  const redo = () => { if (historyIndex < history.length - 1) publishHistory(historyIndex + 1); };
  const colours = { ...DEFAULT_COLOURS, ...layout.colour_settings };
  const visibleEntities = useMemo(() => [...timeline.patients, ...timeline.staff].map((entity) => entityAtTime(entity, time)).filter((entity): entity is RenderedEntity => entity !== null), [time, timeline]);
  const renderedSeats = useMemo(() => {
    const occupied = new Set(visibleEntities.filter((entity) => entity.role === "patient" && entity.seat_id).map((entity) => entity.seat_id));
    return layout.seats.map((seat) => ({ ...seat, occupied: occupied.has(seat.id) }));
  }, [layout.seats, visibleEntities]);
  const colourChange = (state: string, colour: string) => commit({ ...layout, colour_settings: { ...layout.colour_settings, [state]: colour } });

  return <div className="floorplan-root" style={{ minHeight: height }}>
    <main className="floorplan-content">
      {mode === "editor" ? <EditorCanvas layout={layout} onChange={setLayout} onCommit={commit} onUndo={undo} onRedo={redo} canUndo={historyIndex > 0} canRedo={historyIndex < history.length - 1} /> : <SimulationCanvas layout={layout} timeline={timeline} colours={colours} highlight={highlight} time={time} playing={playing} speed={speed} onTime={setTime} onPlaying={setPlaying} onSpeed={setSpeed} />}
    </main>
    <Legend colours={colours} entities={visibleEntities} seats={renderedSeats} collapsed={legendCollapsed} highlight={highlight} onToggle={() => setLegendCollapsed((value) => !value)} onHighlight={setHighlight} onColour={colourChange} onRestore={() => commit({ ...layout, colour_settings: DEFAULT_COLOURS })} />
  </div>;
}
