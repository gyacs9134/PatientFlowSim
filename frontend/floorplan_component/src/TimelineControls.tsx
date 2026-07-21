interface Props {
  playing: boolean;
  time: number;
  duration: number;
  speed: number;
  eventTimes: number[];
  onPlaying: (playing: boolean) => void;
  onTime: (time: number) => void;
  onSpeed: (speed: number) => void;
}

const timeLabel = (minutes: number) => {
  const hour = Math.floor(minutes / 60);
  const minute = Math.floor(minutes % 60);
  const second = Math.floor((minutes % 1) * 60);
  return `${String(hour).padStart(2, "0")}:${String(minute).padStart(2, "0")}:${String(second).padStart(2, "0")}`;
};

export function TimelineControls({ playing, time, duration, speed, eventTimes, onPlaying, onTime, onSpeed }: Props) {
  const nextEvent = () => onTime(eventTimes.find((eventTime) => eventTime > time + 0.0001) ?? duration);
  return <div className="timeline-controls">
    <button onClick={() => onPlaying(!playing)}>{playing ? "Pause" : "Play"}</button>
    <button onClick={() => { onPlaying(false); onTime(0); }}>Reset</button>
    {[1, 2, 5, 10].map((option) => <button className={speed === option ? "active" : ""} key={option} onClick={() => onSpeed(option)}>{option}×</button>)}
    <button onClick={nextEvent}>Next event</button>
    <input aria-label="Simulation timeline" type="range" min={0} max={Math.max(duration, 0.01)} step={0.01} value={time} onChange={(event) => { onPlaying(false); onTime(Number(event.target.value)); }} />
    <strong>{timeLabel(time)} / {timeLabel(duration)}</strong>
  </div>;
}
