import { ORDER_STATUSES, label } from '../utils';

export default function OrderFilters({ filters, onChange, statuses = ORDER_STATUSES, showDates = true }) {
  const set = (k) => (e) => onChange({ ...filters, [k]: e.target.value });
  const hasFilters = Object.values(filters).some(Boolean);
  return (
    <div className="filters">
      <label>
        Status
        <select value={filters.status || ''} onChange={set('status')}>
          <option value="">All</option>
          {statuses.map((s) => (
            <option key={s} value={s}>
              {label(s)}
            </option>
          ))}
        </select>
      </label>
      {showDates && (
        <>
          <label>
            From
            <input type="date" value={filters.date_from || ''} onChange={set('date_from')} />
          </label>
          <label>
            To
            <input type="date" value={filters.date_to || ''} onChange={set('date_to')} />
          </label>
        </>
      )}
      {hasFilters && (
        <button className="btn btn-sm btn-ghost" onClick={() => onChange({})}>
          Clear
        </button>
      )}
    </div>
  );
}
