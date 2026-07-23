import type { AnimatedEntity, Department, HospitalLayout, Keyframe, RenderedEntity, WorldPoint } from "./types";

export const SHAPES = { patient: "circle", nurse: "triangle", doctor: "square" } as const;
export const SATISFACTION_BORDERS = { normal: "#334155", warning: "#eab308", critical: "#dc2626" } as const;

export const snap = (value: number, spacing: number, enabled: boolean): number =>
  enabled ? Math.round(value / spacing) * spacing : value;

export const clamp = (value: number, minimum: number, maximum: number): number =>
  Math.max(minimum, Math.min(maximum, value));

export const departmentOverlap = (first: Department, second: Department): boolean =>
  !(
    first.x_m + first.width_m <= second.x_m ||
    second.x_m + second.width_m <= first.x_m ||
    first.y_m + first.height_m <= second.y_m ||
    second.y_m + second.height_m <= first.y_m
  );

export const overlapWarnings = (layout: HospitalLayout): string[] => {
  const warnings: string[] = [];
  layout.departments.forEach((first, index) => {
    layout.departments.slice(index + 1).forEach((second) => {
      if (departmentOverlap(first, second)) warnings.push(`${first.name} overlaps ${second.name}`);
    });
  });
  return warnings;
};

export const satisfactionBorder = (score = 80): string =>
  score < 40 ? SATISFACTION_BORDERS.critical : score < 60 ? SATISFACTION_BORDERS.warning : SATISFACTION_BORDERS.normal;

export function entityAtTime(entity: AnimatedEntity, time: number): RenderedEntity | null {
  const frames = entity.keyframes;
  if (!frames.length || time < frames[0].time) return null;
  let index = 0;
  while (index + 1 < frames.length && frames[index + 1].time <= time) index += 1;
  const current: Keyframe = frames[index];
  const previous = index > 0 ? frames[index - 1] : undefined;
  const rendered: RenderedEntity = { ...entity, ...current, moving: false };
  const duration = current.travel_duration_min ?? 0;
  const elapsed = time - current.time;
  const source = current.source_location ?? previous;
  if (source && duration > 0 && elapsed >= 0 && elapsed < duration) {
    const progress = clamp(elapsed / duration, 0, 1);
    const point = pointAlongPath(current.path?.length ? current.path : [source, current], progress);
    rendered.x_m = point.x_m;
    rendered.y_m = point.y_m;
    rendered.moving = true;
  }
  rendered.shape = SHAPES[entity.role];
  if (entity.role === "patient") rendered.border = satisfactionBorder(rendered.satisfaction);
  return rendered;
}

export function pointAlongPath(path: WorldPoint[], progress: number): WorldPoint {
  if (!path.length) return { x_m: 0, y_m: 0 };
  if (path.length === 1) return path[0];
  const lengths = path.slice(1).map((point, index) => Math.hypot(point.x_m - path[index].x_m, point.y_m - path[index].y_m));
  const total = lengths.reduce((sum, value) => sum + value, 0);
  if (total === 0) return path[path.length - 1];
  let target = clamp(progress, 0, 1) * total;
  for (let index = 0; index < lengths.length; index += 1) {
    if (target <= lengths[index]) {
      const fraction = lengths[index] === 0 ? 1 : target / lengths[index];
      return {
        x_m: path[index].x_m + (path[index + 1].x_m - path[index].x_m) * fraction,
        y_m: path[index].y_m + (path[index + 1].y_m - path[index].y_m) * fraction,
        department_id: path[index + 1].department_id,
      };
    }
    target -= lengths[index];
  }
  return path[path.length - 1];
}

export function nextKeyframe(entity: AnimatedEntity, time: number): Keyframe | null {
  return entity.keyframes.find((frame) => frame.time > time + 0.000001) ?? null;
}

export const stateCounts = (entities: RenderedEntity[]): Record<string, number> =>
  entities.reduce<Record<string, number>>((counts, entity) => {
    counts[entity.state] = (counts[entity.state] ?? 0) + 1;
    return counts;
  }, {});
