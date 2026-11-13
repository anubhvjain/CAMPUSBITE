import { LIFECYCLE, label } from '../utils';

export default function StatusTracker({ status }) {
  if (status === 'CANCELLED' || status === 'REFUNDED') {
    return <div className={`tracker-terminal tracker-${status.toLowerCase()}`}>Order {label(status)}</div>;
  }
  const current = LIFECYCLE.indexOf(status);
  return (
    <ol className="tracker">
      {LIFECYCLE.map((s, i) => (
        <li key={s} className={i < current ? 'done' : i === current ? 'current' : ''}>
          <span className="dot" />
          <span className="tracker-label">{label(s)}</span>
        </li>
      ))}
    </ol>
  );
}
