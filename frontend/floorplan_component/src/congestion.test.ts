import { describe, expect, it } from "vitest";
import { classifyCongestion, queueSnapshots } from "./congestion";
import type { HospitalLayout, RenderedEntity } from "./types";

const layout = {
  schema_version: 1, name: "test", canvas_width_m: 10, canvas_height_m: 10, grid_spacing_m: .5,
  departments: [], seats: [], resource_stations: [], entry_points: [], exit_points: [],
  queue_points: [{ id: "q", x_m: 1, y_m: 1, point_type: "triage", department_id: "triage", direction: "horizontal" }],
  colour_settings: {},
} satisfies HospitalLayout;

describe("live congestion rules", () => {
  it("uses transparent severity thresholds", () => {
    expect(classifyCongestion(0, 0, 2, .2)).toBe("normal");
    expect(classifyCongestion(3, 0, 2, .2)).toBe("busy");
    expect(classifyCongestion(5, 0, 2, .2)).toBe("congested");
    expect(classifyCongestion(7, 0, 2, .2)).toBe("critical");
  });
  it("keeps queue counts and current longest wait deterministic", () => {
    const entity = { id: "P1", role: "patient", shape: "circle", state: "waiting_triage", x_m: 1, y_m: 1, time: 5, moving: false, keyframes: [], queue_type: "triage", queue_position: 0, queue_entered_time: 5 } as RenderedEntity;
    expect(queueSnapshots([entity], 12, layout)[0]).toMatchObject({ queueLength: 1, longestWait: 7 });
  });
});
