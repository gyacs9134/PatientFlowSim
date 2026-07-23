import type { Department, DepartmentPressure, HospitalLayout, QueueSnapshot, RenderedEntity, Timeline } from "./types";

export const QUEUE_LABELS: Record<string, string> = {
  check_in: "Check-in",
  triage: "Triage",
  initial_consultation: "Initial consultation",
  laboratory: "Laboratory",
  imaging: "Imaging",
  return_check_in: "Return check-in",
  return_consultation: "Return consultation",
};

export const CONGESTION_COLOURS = {
  normal: "#64748b",
  busy: "#d97706",
  congested: "#ea580c",
  critical: "#dc2626",
} as const;

export function classifyCongestion(queueLength: number, longestWait: number, capacity: number, utilisation: number) {
  const safeCapacity = Math.max(1, capacity);
  const pressure = queueLength / safeCapacity;
  if (pressure > 3 || longestWait >= 60 || (utilisation >= 0.95 && pressure > 1)) return "critical" as const;
  if (pressure > 2 || longestWait >= 30 || (utilisation >= 0.9 && pressure > 0.5)) return "congested" as const;
  if (pressure > 1 || longestWait >= 15 || utilisation >= 0.75) return "busy" as const;
  return "normal" as const;
}

export function queueSnapshots(entities: RenderedEntity[], time: number, layout: HospitalLayout): QueueSnapshot[] {
  return layout.queue_points.map((point) => {
    const waiting = entities.filter((entity) => entity.role === "patient" && entity.queue_type === point.point_type && entity.queue_position !== null && entity.queue_position !== undefined);
    const longestWait = waiting.reduce((maximum, entity) => Math.max(maximum, time - Number(entity.queue_entered_time ?? time)), 0);
    return {
      queueType: point.point_type,
      label: QUEUE_LABELS[point.point_type] ?? point.point_type,
      departmentId: point.department_id ?? null,
      queueLength: waiting.length,
      longestWait: Math.max(0, longestWait),
    };
  });
}

export function resourceUtilisation(resource: string, time: number, timeline: Timeline): number {
  const capacity = Math.max(1, Number(timeline.resource_capacity?.[resource] ?? 1));
  if (time <= 0) return 0;
  const busy = (timeline.resource_intervals?.[resource] ?? []).reduce(
    (total, [start, end]) => total + (start < time ? Math.max(0, Math.min(time, end) - start) : 0),
    0,
  );
  return Math.min(1, busy / (capacity * time));
}

function resourceForDepartment(department: Department): string {
  if (department.department_type === "consultation room") return "doctors";
  if (department.department_type === "triage") return "triage_nurses";
  if (department.department_type === "check-in") return "check_in";
  if (department.department_type === "laboratory") return "laboratory";
  if (department.department_type === "imaging") return "imaging";
  return "";
}

export function departmentPressures(layout: HospitalLayout, queues: QueueSnapshot[], timeline: Timeline, time: number): Record<string, DepartmentPressure> {
  const result: Record<string, DepartmentPressure> = {};
  layout.departments.forEach((department) => {
    const matching = queues.filter((queue) => queue.departmentId === department.id);
    const queueLength = matching.reduce((sum, queue) => sum + queue.queueLength, 0);
    const longestWait = matching.reduce((maximum, queue) => Math.max(maximum, queue.longestWait), 0);
    const resource = resourceForDepartment(department);
    const capacity = Math.max(1, Number(timeline.resource_capacity?.[resource] ?? 1));
    const utilisation = resource ? resourceUtilisation(resource, time, timeline) : 0;
    result[department.id] = {
      departmentId: department.id,
      queueLength,
      longestWait,
      capacity,
      utilisation,
      status: classifyCongestion(queueLength, longestWait, capacity, utilisation),
    };
  });
  return result;
}
