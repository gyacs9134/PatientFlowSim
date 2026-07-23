import { useEffect, useRef, useState } from "react";
import { Circle, Group, Layer, Rect, Stage, Text } from "react-konva";
import type { HospitalLayout } from "./types";

export function PreviewCanvas({ layout }: { layout: HospitalLayout }) {
  const host = useRef<HTMLDivElement>(null);
  const [size, setSize] = useState({ width: 760, height: 480 });
  useEffect(() => {
    if (!host.current) return;
    const observer = new ResizeObserver(([entry]) => setSize({ width: Math.max(420, entry.contentRect.width), height: Math.max(360, entry.contentRect.height) }));
    observer.observe(host.current);
    return () => observer.disconnect();
  }, []);
  const scale = Math.min((size.width - 28) / layout.canvas_width_m, (size.height - 28) / layout.canvas_height_m);
  const offset = { x: (size.width - layout.canvas_width_m * scale) / 2, y: (size.height - layout.canvas_height_m * scale) / 2 };
  return <div className="preview-canvas" ref={host}>
    <Stage width={size.width} height={size.height} x={offset.x} y={offset.y}>
      <Layer listening={false}>
        <Rect width={layout.canvas_width_m * scale} height={layout.canvas_height_m * scale} fill="#f8fafc" stroke="#334155" strokeWidth={2} cornerRadius={5} />
        {layout.departments.map((department) => <Group key={department.id}>
          <Rect x={department.x_m * scale} y={department.y_m * scale} width={department.width_m * scale} height={department.height_m * scale} fill={department.fill} stroke={department.border} strokeWidth={1.5} cornerRadius={3} />
          <Text x={(department.x_m + .12) * scale} y={(department.y_m + .12) * scale} width={Math.max(10, (department.width_m - .24) * scale)} text={department.name} fontSize={Math.max(8, scale * .23)} fontStyle="600" fill="#172033" />
        </Group>)}
        {layout.seats.map((seat) => <Rect key={seat.id} x={seat.x_m * scale} y={seat.y_m * scale} offsetX={scale * .12} offsetY={scale * .12} width={scale * .24} height={scale * .24} rotation={seat.rotation_deg} fill={seat.available ? "#fff" : "#94a3b8"} stroke="#64748b" strokeWidth={1} />)}
        {layout.resource_stations.map((station) => <Circle key={station.id} x={station.x_m * scale} y={station.y_m * scale} radius={Math.max(2.5, scale * .11)} fill="#0f766e" stroke="#134e4a" />)}
      </Layer>
    </Stage>
  </div>;
}
