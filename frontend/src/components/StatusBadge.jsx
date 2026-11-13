import { label } from '../utils';

export default function StatusBadge({ status, kind = 'order' }) {
  if (!status) return null;
  return <span className={`badge badge-${kind}-${status.toLowerCase()}`}>{label(status)}</span>;
}
