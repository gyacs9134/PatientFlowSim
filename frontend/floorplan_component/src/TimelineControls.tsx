interface Props {
  playing: boolean;
  time: number;
  startTime: number;
  endTime: number;
  speed: number;
  eventTimes: number[];
  showFinish: boolean;
  onPlaying: (playing: boolean) => void;
  onTime: (time: number) => void;
  onSpeed: (speed: number) => void;
  onFinish: () => void;
  onFit: () => void;
}

export const timeLabel = (minutes: number) => {
  const hour = Math.floor(minutes / 60);
  const minute = Math.floor(minutes % 60);
  const second = Math.floor((minutes % 1) * 60);
  return `${String(hour).padStart(2, "0")}:${String(minute).padStart(2, "0")}:${String(second).padStart(2, "0")}`;
};

export function TimelineControls({ playing, time, startTime, endTime, speed, eventTimes, showFinish, onPlaying, onTime, onSpeed, onFinish, onFit }: Props) {
  const nextEvent = () => onTime(eventTimes.find((eventTime) => eventTime > time + 0.0001 && eventTime <= endTime) ?? endTime);
  return <div className="timeline-controls">
    <button className="play-control" aria-label={playing ? "Pause" : "Play"} onClick={() => onPlaying(!playing)}>{playing ? "Ⅱ Pause" : "▶ Play"}</button>
    <button title="Restart replay" onClick={() => { onPlaying(false); onTime(startTime); }}>↺ Restart</button>
    <button title="Jump to next event" onClick={nextEvent}>⇥ Next</button>
    <div className="speed-group" aria-label="Playback speed">{[1, 2, 5, 10].map((option) => <button className={speed === option ? "active" : ""} key={option} onClick={() => onSpeed(option)}>{option}×</button>)}</div>
    <button title="Fit floor plan to the visible area" onClick={onFit}>⛶ Fit</button>
    <input aria-label="Simulation timeline" type="range" min={startTime} max={Math.max(endTime, startTime + .01)} step={0.01} value={time} onChange={(event) => { onPlaying(false); onTime(Number(event.target.value)); }} />
    <strong>{timeLabel(time)} <span>/ {timeLabel(endTime)}</span></strong>
    {showFinish && <button className="finish-control" onClick={onFinish}>Finish run</button>}
  </div>;
}
