# GIF export

The results screen exports the full run or a selected replay period. Users choose start/end time, 10/15/20 FPS, dimensions, playback speed, loop behaviour, and inclusion of IDs, room dimensions, legend, metrics, and satisfaction labels.

Python Pillow renders the saved JSON layout and the same prepared animation timeline used by the browser. `imageio` encodes frames when available; Pillow is a tested fallback. Rooms, marker shapes/colours, satisfaction borders, seat occupancy, time, live metrics, and optional legend are preserved.

Requested frames are evenly sampled and capped. A pixel-count guard rejects unsafe combinations before allocation, and Streamlit reports rendering progress. GIF files are recordings only and never replace editable layout JSON.
