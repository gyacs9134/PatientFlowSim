# 2D floor-plan editor

The editor is a custom Streamlit component built with React, TypeScript, Konva, and React-Konva. Python owns validation and persistence; the browser owns responsive pointer interaction. It sends a layout to Python only after a meaningful edit, not during every rendered frame.

## Coordinates and schema

Every permanent position and dimension is stored in metres. Screen pixels are derived from the viewport scale and are never written to JSON. Schema version 1 contains the canvas width and height, grid spacing, rectangular departments, seats, resource stations, entry and exit points, stable queue anchors, and patient-state colours. `config/default_layout.json` is the bundled example.

Departments have positive width and height and must remain inside the canvas. Seats must refer to an initial or return waiting-area department. Resource and point references must target known departments. Imported JSON produces readable errors for malformed JSON, invalid dimensions, unsupported object types, missing cross-references, or unknown colour states. Department overlaps are warnings because overlap can be intentional during editing.

## Editing

The canvas supports wheel zoom, dragging empty space to pan, fit, reset, centre, metre grid selection, optional snapping, keyboard deletion, Shift-click multi-selection, and a 50-step undo/redo history. Rooms can be created, moved, transformed using edge or corner handles, duplicated, renamed, recoloured, retyped, or edited numerically. Live labels show X, Y, width, and height in metres.

Seats are independent objects with position, rotation, waiting-area assignment, availability, occupancy, and current patient fields. The seat-grid tool creates rows and columns with configurable spacing. Check-in, triage, doctor, laboratory, and imaging stations visually map to simulation resources; the dashboard warns if a layout has fewer visible stations than the configured capacity.

Saved layouts are regular JSON. Layout Management supports load, save, duplicate, import, export, delete, and reset. Files written to a Streamlit Community Cloud instance may be ephemeral after the app restarts, so download important layouts.

The MVP deliberately supports only rectangular rooms and one floor. It does not import CAD drawings or provide shared multi-user editing.
