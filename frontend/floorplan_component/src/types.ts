export type DepartmentType =
  | "entrance"
  | "check-in"
  | "triage"
  | "initial waiting area"
  | "consultation room"
  | "laboratory"
  | "imaging"
  | "return waiting area"
  | "exit";

export interface Department {
  id: string;
  name: string;
  department_type: DepartmentType;
  x_m: number;
  y_m: number;
  width_m: number;
  height_m: number;
  fill: string;
  border: string;
}

export interface Seat {
  id: string;
  x_m: number;
  y_m: number;
  rotation_deg: number;
  waiting_area_id: string;
  available: boolean;
  occupied: boolean;
  patient_id: string | null;
}

export interface ResourceStation {
  id: string;
  station_type: string;
  x_m: number;
  y_m: number;
  department_id: string | null;
  resource_index: number;
  label: string;
}

export interface LayoutPoint {
  id: string;
  x_m: number;
  y_m: number;
  point_type: string;
  department_id?: string | null;
  direction?: "horizontal" | "vertical";
}

export interface HospitalLayout {
  schema_version: 1;
  name: string;
  canvas_width_m: number;
  canvas_height_m: number;
  grid_spacing_m: 0.25 | 0.5 | 1;
  departments: Department[];
  seats: Seat[];
  resource_stations: ResourceStation[];
  entry_points: LayoutPoint[];
  exit_points: LayoutPoint[];
  queue_points: LayoutPoint[];
  colour_settings: Record<string, string>;
}

export interface Keyframe {
  time: number;
  x_m: number;
  y_m: number;
  state: string;
  department_id?: string | null;
  satisfaction?: number;
  seat_id?: string | null;
  travel_duration_min?: number;
  simulation_timestamp?: number;
  movement_start_time?: number;
  movement_end_time?: number;
  source_location?: WorldPoint;
  destination_location?: WorldPoint;
  path?: WorldPoint[];
  queue_position?: number | null;
  queue_type?: string | null;
  queue_entered_time?: number | null;
  resource_station_id?: string | null;
  event_type?: string;
  satisfaction_event?: { event: string; score_change: number; time: number };
  [key: string]: unknown;
}

export interface WorldPoint {
  x_m: number;
  y_m: number;
  department_id?: string | null;
}

export interface AnimatedEntity {
  id: string;
  role: "patient" | "nurse" | "doctor";
  shape: "circle" | "triangle" | "square";
  station_id?: string;
  keyframes: Keyframe[];
  details?: Record<string, unknown>;
}

export interface Timeline {
  duration: number;
  patients: AnimatedEntity[];
  staff: AnimatedEntity[];
  seats: Seat[];
  colours?: Record<string, string>;
  shape_rules?: Record<string, string>;
  resource_capacity?: Record<string, number>;
  resource_intervals?: Record<string, [number, number][]>;
}

export interface RenderedEntity extends AnimatedEntity, Keyframe {
  moving: boolean;
  border?: string;
}

export interface ComponentArgs {
  layout: HospitalLayout;
  timeline: Timeline;
  mode: "preview" | "editor" | "simulation";
  height: number;
  autoPlay?: boolean;
  startTime?: number;
  endTime?: number;
  playbackSpeed?: number;
  showFinish?: boolean;
}

export type CongestionStatus = "normal" | "busy" | "congested" | "critical";

export interface QueueSnapshot {
  queueType: string;
  label: string;
  departmentId: string | null;
  queueLength: number;
  longestWait: number;
}

export interface DepartmentPressure {
  departmentId: string;
  queueLength: number;
  longestWait: number;
  capacity: number;
  utilisation: number;
  status: CongestionStatus;
}

export interface OverlaySettings {
  congestion: boolean;
  queueLabels: boolean;
  flowTrails: boolean;
  seatOccupancy: boolean;
  averageWait: boolean;
  utilisation: boolean;
  satisfaction: boolean;
  patientIds: boolean;
}
