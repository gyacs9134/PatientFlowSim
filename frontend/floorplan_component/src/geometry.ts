import type { AnimatedEntity, Department, HospitalLayout, Keyframe, RenderedEntity } from "./types";

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
  if (previous && duration > 0 && elapsed >= 0 && elapsed < duration) {
    const progress = clamp(elapsed / duration, 0, 1);
    rendered.x_m = previous.x_m + (current.x_m - previous.x_m) * progress;
    rendered.y_m = previous.y_m + (current.y_m - previous.y_m) * progress;
    rendered.moving = true;
  }
  rendered.shape = SHAPES[entity.role];
  if (entity.role === "patient") rendered.border = satisfactionBorder(rendered.satisfaction);
  return rendered;
}

export const stateCounts = (entities: RenderedEntity[]): Record<string, number> =>
  entities.reduce<Record<string, number>>((counts, entity) => {
    counts[entity.state] = (counts[entity.state] ?? 0) + 1;
    return counts;
  }, {});
