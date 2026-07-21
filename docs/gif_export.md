# GIF export

GIF export uses the same saved layout and Python spatial timeline as interactive playback. Pillow draws departments, seats, patient circles, nurse triangles, doctor squares, workflow colours, satisfaction borders, optional IDs and score labels, and optional fixed legend and metrics panels. ImageIO encodes the rendered frames as a downloadable GIF.

Users choose the complete run or a start/end range, playback speed, 10/15/20 FPS, output dimensions, looping, and optional overlays. Simulation time is sampled evenly. `max_frames` caps long clinic days, so lowering the cap shortens export time and memory use without changing the underlying simulation. A separate pixel-count guard rejects unsafe combinations of frame count and resolution with a readable error.

GIFs are presentation outputs only. They do not contain editable layout metadata; export or save the JSON layout separately. The renderer is intentionally diagrammatic rather than an architectural rasterizer, and it uses direct station-to-station movement without wall-aware pathfinding.

For automation, call `patientflowsim.gif_export.render_gif(layout, timeline, GifExportConfig(...))`. The return value is GIF bytes suitable for a file, HTTP response, or Streamlit download button. An optional progress callback receives values from 0 to 1 after each frame.
