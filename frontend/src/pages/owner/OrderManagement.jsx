import { useState } from 'react';
import { Link } from 'react-router-dom';
import { ownerApi } from '../../api';
import { errorMessage } from '../../api/client';
import ErrorMessage from '../../components/ErrorMessage';
import Loader from '../../components/Loader';
import OrderFilters from '../../components/OrderFilters';
import OrderItemsList from '../../components/OrderItemsList';
import Pagination from '../../components/Pagination';
import StatusBadge from '../../components/StatusBadge';
import { useAsync } from '../../hooks';
import { dateTime, money } from '../../utils';

// Next step an owner can take from each status (mirrors backend rules)
const NEXT = { PLACED: 'ACCEPTED', ACCEPTED: 'PREPARING', PREPARING: 'READY' };
const NEXT_LABEL = { ACCEPTED: 'Accept order', PREPARING: 'Start preparing', READY: 'Mark ready' };

export default function OrderManagement() {
  const [filters, setFilters] = useState({});
  const [page, setPage] = useState(1);
  const [picked, setPicked] = useState({});
  const [actionError, setActionError] = useState('');
  const [busy, setBusy] = useState(null);
  const orders = useAsync(() => ownerApi.orders({ ...filters, page, page_size: 8 }), [filters, page]);
  const partners = useAsync(() => ownerApi.partners(), []);

  const act = async (id, fn) => {
    setBusy(id);
    setActionError('');
    try {
      await fn();
      orders.reload();
    } catch (e) {
      setActionError(`Order #${id}: ${errorMessage(e)}`);
    } finally {
      setBusy(null);
    }
  };

  return (
    <div className="container page">
      <div className="page-header">
        <h1>Incoming orders</h1>
        <button className="btn btn-sm btn-ghost" onClick={orders.reload}>↻ Refresh</button>
      </div>
      <OrderFilters filters={filters} onChange={(f) => { setFilters(f); setPage(1); }} />
      <ErrorMessage message={orders.error || actionError} onRetry={orders.error ? orders.reload : undefined} />
      {orders.loading && !orders.data ? (
        <Loader />
      ) : orders.data?.items.length === 0 ? (
        <p className="empty">No orders match these filters.</p>
      ) : (
        <div className="order-list">
          {orders.data?.items.map((o) => {
            const next = NEXT[o.status];
            return (
              <article key={o.id} className="card order-card">
                <div className="order-card-head">
                  <div>
                    <Link to={`/orders/${o.id}`}><strong>Order #{o.id}</strong></Link>
                    <div className="muted small">{dateTime(o.created_at)} · {o.delivery_address}</div>
                  </div>
                  <StatusBadge status={o.status} />
                </div>
                <OrderItemsList items={o.items} />
                {o.notes && <p className="muted small">📝 {o.notes}</p>}
                <div className="order-meta">
                  <span>Total <strong>{money(o.total_amount)}</strong></span>
                  <span>Payment <StatusBadge kind="payment" status={o.payment_status} /></span>
                  {o.return_status !== 'none' && <span>Return <StatusBadge kind="return" status={o.return_status} /></span>}
                </div>
                <div className="actions">
                  {next && (
                    <button className="btn btn-sm" disabled={busy === o.id}
                      onClick={() => act(o.id, () => ownerApi.updateStatus(o.id, next))}>
                      {NEXT_LABEL[next]}
                    </button>
                  )}
                  {o.status === 'PLACED' && (
                    <button className="btn btn-sm btn-danger" disabled={busy === o.id}
                      onClick={() => window.confirm('Reject and cancel this order?') && act(o.id, () => ownerApi.updateStatus(o.id, 'CANCELLED'))}>
                      Reject
                    </button>
                  )}
                  {o.status === 'READY' && (
                    <div className="assign">
                      <select value={picked[o.id] || ''} onChange={(e) => setPicked({ ...picked, [o.id]: e.target.value })}>
                        <option value="">Choose delivery partner…</option>
                        {partners.data?.map((p) => (
                          <option key={p.id} value={p.id}>{p.name}{p.phone ? ` (${p.phone})` : ''}</option>
                        ))}
                      </select>
                      <button className="btn btn-sm" disabled={!picked[o.id] || busy === o.id}
                        onClick={() => act(o.id, () => ownerApi.assign(o.id, Number(picked[o.id])))}>
                        Assign
                      </button>
                    </div>
                  )}
                </div>
              </article>
            );
          })}
        </div>
      )}
      {orders.data && <Pagination page={orders.data.page} pages={orders.data.pages} total={orders.data.total} onChange={setPage} />}
    </div>
  );
}
