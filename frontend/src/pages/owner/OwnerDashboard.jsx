import { Link } from 'react-router-dom';
import { ownerApi } from '../../api';
import ErrorMessage from '../../components/ErrorMessage';
import Loader from '../../components/Loader';
import StatusBadge from '../../components/StatusBadge';
import { useAsync } from '../../hooks';
import { dateTime, money } from '../../utils';

function StatCard({ title, value, hint, to }) {
  const body = (
    <div className="card stat-card">
      <span className="muted small">{title}</span>
      <strong>{value}</strong>
      {hint && <span className="muted small">{hint}</span>}
    </div>
  );
  return to ? <Link to={to}>{body}</Link> : body;
}

export default function OwnerDashboard() {
  const restaurant = useAsync(() => ownerApi.restaurant(), []);
  const stats = useAsync(() => ownerApi.stats(), []);
  const reminders = useAsync(() => ownerApi.reminders({ page_size: 10 }), []);

  const refresh = async () => {
    await ownerApi.refreshReminders();
    reminders.reload();
    stats.reload();
  };
  const dismiss = async (id) => {
    await ownerApi.dismissReminder(id);
    reminders.reload();
    stats.reload();
  };

  if (stats.loading && !stats.data) return <Loader />;
  const s = stats.data;

  return (
    <div className="container page">
      <div className="page-header">
        <div>
          <h1>{restaurant.data?.name || 'Your restaurant'}</h1>
          <p className="muted">Restaurant dashboard</p>
        </div>
        <div className="actions">
          <Link to="/owner/orders" className="btn">Manage orders</Link>
          <Link to="/owner/menu" className="btn btn-ghost">Manage menu</Link>
        </div>
      </div>
      <ErrorMessage message={stats.error || restaurant.error} onRetry={stats.reload} />

      <section className="card card-body reminders">
        <div className="section-head">
          <h2>⏰ Reminders {reminders.data?.total ? <span className="count-pill">{reminders.data.total}</span> : null}</h2>
          <button className="btn btn-sm btn-ghost" onClick={refresh}>Check now</button>
        </div>
        <ErrorMessage message={reminders.error} />
        {reminders.data?.items.length ? (
          <ul className="reminder-list">
            {reminders.data.items.map((r) => (
              <li key={r.id}>
                <div>
                  <Link to={`/orders/${r.order_id}`}>{r.message}</Link>
                  <div className="muted small">{dateTime(r.created_at)}</div>
                </div>
                <button className="btn btn-sm btn-ghost" onClick={() => dismiss(r.id)}>Dismiss</button>
              </li>
            ))}
          </ul>
        ) : (
          <p className="muted">All caught up — no stale orders.</p>
        )}
      </section>

      {s && (
        <>
          <div className="stats-grid">
            <StatCard title="Total orders" value={s.total_orders} hint={`${s.orders_today} today`} to="/owner/orders" />
            <StatCard title="Revenue (paid)" value={money(s.total_revenue)} hint={`${money(s.refunded_amount)} refunded`} />
            <StatCard title="Avg rating" value={s.avg_rating ? `⭐ ${s.avg_rating.toFixed(1)}` : '—'} hint={`${s.review_count} reviews`} />
            <StatCard title="Pending returns" value={s.pending_returns} to="/owner/returns" />
          </div>
          <div className="two-col">
            <div className="card card-body">
              <h3>Orders by status</h3>
              <ul className="status-bars">
                {Object.entries(s.status_counts).map(([st, n]) => (
                  <li key={st}>
                    <StatusBadge status={st} />
                    <div className="bar"><div style={{ width: `${s.total_orders ? (n / s.total_orders) * 100 : 0}%` }} /></div>
                    <span>{n}</span>
                  </li>
                ))}
              </ul>
            </div>
            <div className="card card-body">
              <h3>Top dishes</h3>
              {s.top_dishes.length ? (
                <ol className="top-dishes">
                  {s.top_dishes.map((d) => (
                    <li key={d.name}><span>{d.name}</span><strong>{d.quantity} sold</strong></li>
                  ))}
                </ol>
              ) : (
                <p className="muted">No sales yet.</p>
              )}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
