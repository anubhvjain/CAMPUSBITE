import { useState } from 'react';
import { deliveryApi } from '../../api';
import { errorMessage } from '../../api/client';
import ErrorMessage from '../../components/ErrorMessage';
import Loader from '../../components/Loader';
import OrderFilters from '../../components/OrderFilters';
import OrderItemsList from '../../components/OrderItemsList';
import Pagination from '../../components/Pagination';
import StatusBadge from '../../components/StatusBadge';
import { useAsync } from '../../hooks';
import { dateTime, money } from '../../utils';

const NEXT = { ASSIGNED: ['OUT_FOR_DELIVERY', 'Picked up — out for delivery'], OUT_FOR_DELIVERY: ['DELIVERED', 'Mark delivered'] };

export default function DeliveryDashboard() {
  const [filters, setFilters] = useState({});
  const [page, setPage] = useState(1);
  const [busy, setBusy] = useState(null);
  const [actionError, setActionError] = useState('');
  const { data, loading, error, reload } = useAsync(
    () => deliveryApi.orders({ status: filters.status, page, page_size: 8 }),
    [filters, page],
  );

  const advance = async (o) => {
    const [status] = NEXT[o.status];
    setBusy(o.id);
    setActionError('');
    try {
      await deliveryApi.updateStatus(o.id, status);
      reload();
    } catch (e) {
      setActionError(errorMessage(e));
    } finally {
      setBusy(null);
    }
  };

  return (
    <div className="container page">
      <div className="page-header">
        <div>
          <h1>My deliveries</h1>
          <p className="muted">Orders assigned to you (active by default).</p>
        </div>
        <button className="btn btn-sm btn-ghost" onClick={reload}>↻ Refresh</button>
      </div>
      <OrderFilters filters={filters} showDates={false} statuses={['ASSIGNED', 'OUT_FOR_DELIVERY', 'DELIVERED', 'REFUNDED']}
        onChange={(f) => { setFilters(f); setPage(1); }} />
      <ErrorMessage message={error || actionError} onRetry={error ? reload : undefined} />
      {loading && !data ? (
        <Loader />
      ) : data?.items.length === 0 ? (
        <p className="empty">No deliveries right now. 🛵</p>
      ) : (
        <div className="order-list">
          {data?.items.map((o) => (
            <article key={o.id} className="card order-card">
              <div className="order-card-head">
                <div>
                  <strong>Order #{o.id} · {o.restaurant_name}</strong>
                  <div className="muted small">Updated {dateTime(o.updated_at)}</div>
                </div>
                <StatusBadge status={o.status} />
              </div>
              <div className="delivery-info">
                <div><span className="muted small">Customer</span><strong>{o.customer?.name}</strong></div>
                <div><span className="muted small">Phone</span>{o.customer?.phone ? <a href={`tel:${o.customer.phone}`}>{o.customer.phone}</a> : '—'}</div>
                <div><span className="muted small">Address</span>{o.delivery_address}</div>
              </div>
              <OrderItemsList items={o.items} />
              <div className="order-meta"><span>Total <strong>{money(o.total_amount)}</strong></span></div>
              {NEXT[o.status] && (
                <div className="actions">
                  <button className="btn" disabled={busy === o.id} onClick={() => advance(o)}>{NEXT[o.status][1]}</button>
                </div>
              )}
            </article>
          ))}
        </div>
      )}
      {data && <Pagination page={data.page} pages={data.pages} total={data.total} onChange={setPage} />}
    </div>
  );
}
