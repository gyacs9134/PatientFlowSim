import { describe, expect, it } from "vitest";
import { entityAtTime, pointAlongPath, satisfactionBorder, SHAPES, snap, stateCounts } from "./geometry";
import type { AnimatedEntity } from "./types";

const patient: AnimatedEntity = {
  id: "P1", role: "patient", shape: "circle", keyframes: [
    { time: 2, x_m: 1, y_m: 1, state: "arrived_check_in", satisfaction: 80 },
    { time: 4, x_m: 3, y_m: 1, state: "waiting_triage", satisfaction: 30, travel_duration_min: 1 },
  ],
};

describe("spatial geometry rules", () => {
  it("keeps role shapes immutable", () => expect(SHAPES).toEqual({ patient: "circle", nurse: "triangle", doctor: "square" }));
  it("hides people before arrival", () => expect(entityAtTime(patient, 1)).toBeNull());
  it("uses satisfaction border without changing state", () => {
    const rendered = entityAtTime(patient, 4)!;
    expect(rendered.shape).toBe("circle"); expect(rendered.state).toBe("waiting_triage"); expect(rendered.border).toBe(satisfactionBorder(30));
  });
  it("snaps only when enabled", () => { expect(snap(1.24, 0.5, true)).toBe(1); expect(snap(1.24, 0.5, false)).toBe(1.24); });
  it("derives live legend counts", () => expect(stateCounts([entityAtTime(patient, 2)!])).toEqual({ arrived_check_in: 1 }));
  it("interpolates along stable waypoints", () => {
    expect(pointAlongPath([{ x_m: 0, y_m: 0 }, { x_m: 2, y_m: 0 }, { x_m: 2, y_m: 2 }], .75)).toMatchObject({ x_m: 2, y_m: 1 });
  });
});
