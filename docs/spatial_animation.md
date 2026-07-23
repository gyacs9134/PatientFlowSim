# Spatial animation

Python converts each logged patient event to a typed spatial keyframe. The event's `simulation_timestamp` remains unchanged. A separate monotonic visual `time` serialises movements that share the same SimPy timestamp, preventing instantaneous jumps when arrival and service start occur together.

Each keyframe can contain source and destination locations, movement start/end, a direct waypoint path, queue type/index/entry time, seat, station, satisfaction, and event metadata. Walking duration is total waypoint distance divided by the configurable speed, default 1.2 m/s. Entrance and discharge paths extend just outside the map so patients visibly enter and leave.

The browser interpolates along path segments with `requestAnimationFrame`. Stationary patients retain exact queue or seat coordinates. Examination patients travel to laboratory/imaging in cyan, return in red, re-enter check-in, and wait for a return consultation in dark red.

The same seed, configuration, event log, and layout produce byte-equivalent timeline JSON. Direct waypoints are an MVP approximation; walls and obstacles are not considered.
