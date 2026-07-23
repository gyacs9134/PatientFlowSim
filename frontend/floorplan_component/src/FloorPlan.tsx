import { useEffect, useRef, useState } from "react";
import { Streamlit } from "streamlit-component-lib";
import { EditorCanvas } from "./EditorCanvas";
import { PreviewCanvas } from "./PreviewCanvas";
import { SimulationScreen } from "./SimulationScreen";
import type { ComponentArgs, HospitalLayout } from "./types";

export const DEFAULT_COLOURS: Record<string, string> = {
  arrived_check_in: "#2563eb",
  waiting_triage: "#eab308",
  waiting_initial_consultation: "#f97316",
  consultation: "#7c3aed",
  travelling_examination: "#06b6d4",
  examination: "#0e7490",
  returning_examination: "#ef4444",
  waiting_return_consultation: "#991b1b",
  discharged: "#64748b",
};

export function FloorPlan({ layout: initialLayout, timeline, mode, height, autoPlay = false, startTime = 0, endTime, playbackSpeed = 10, showFinish = true }: ComponentArgs) {
  const [layout, setLayout] = useState<HospitalLayout>(initialLayout);
  const [history, setHistory] = useState<HospitalLayout[]>([initialLayout]);
  const [historyIndex, setHistoryIndex] = useState(0);
  const lastPythonLayout = useRef(JSON.stringify(initialLayout));

  useEffect(() => {
    const incoming = JSON.stringify(initialLayout);
    if (incoming !== lastPythonLayout.current) {
      lastPythonLayout.current = incoming;
      setLayout(initialLayout);
      setHistory([initialLayout]);
      setHistoryIndex(0);
    }
  }, [initialLayout]);
  useEffect(() => { Streamlit.setFrameHeight(height); }, [height, layout, mode]);

  const commit = (next: HospitalLayout) => {
    setLayout(next);
    const branch = history.slice(0, historyIndex + 1);
    const nextHistory = [...branch, next].slice(-50);
    setHistory(nextHistory);
    setHistoryIndex(nextHistory.length - 1);
    lastPythonLayout.current = JSON.stringify(next);
    Streamlit.setComponentValue({ type: "layout_changed", layout: next });
  };
  const publishHistory = (index: number) => {
    const next = history[index];
    setHistoryIndex(index);
    setLayout(next);
    lastPythonLayout.current = JSON.stringify(next);
    Streamlit.setComponentValue({ type: "layout_changed", layout: next });
  };
  const undo = () => { if (historyIndex > 0) publishHistory(historyIndex - 1); };
  const redo = () => { if (historyIndex < history.length - 1) publishHistory(historyIndex + 1); };
  const colours = { ...DEFAULT_COLOURS, ...layout.colour_settings, ...timeline.colours };

  if (mode === "preview") return <div className="floorplan-preview-root" style={{ height }}><PreviewCanvas layout={layout} /></div>;
  if (mode === "editor") return <div className="floorplan-root editor-root" style={{ height }}>
    <EditorCanvas layout={layout} onChange={setLayout} onCommit={commit} onUndo={undo} onRedo={redo} canUndo={historyIndex > 0} canRedo={historyIndex < history.length - 1} />
  </div>;
  return <div className="floorplan-root live-root" style={{ height }}>
    <SimulationScreen layout={layout} timeline={timeline} initialColours={colours} autoPlay={autoPlay} startTime={startTime} endTime={endTime ?? timeline.duration} playbackSpeed={playbackSpeed} showFinish={showFinish} />
  </div>;
}
