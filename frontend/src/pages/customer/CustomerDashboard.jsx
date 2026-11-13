import { useState } from 'react';
import { Link } from 'react-router-dom';
import { orderApi } from '../../api';
import { errorMessage } from '../../api/client';
import ErrorMessage from '../../components/ErrorMessage';
import Loader from '../../components/Loader';
import OrderFilters from '../../components/OrderFilters';
import OrderItemsList from '../../components/OrderItemsList';
import Pagination from '../../components/Pagination';
import StatusBadge from '../../components/StatusBadge';
import { ReturnModal, ReviewModal } from './OrderActions';
import { useAsync } from '../../hooks';
import { dateTime, money } from '../../utils';

const ACTIVE = ['PLACED', 'ACCEPTED', 'PREPARING', 'READY', 'ASSIGNED', 'OUT_FOR_DELIVERY'];

export default function CustomerDashboard() {
  const [filters, setFilters] = useState({});
  const [page, setPage] = useState(1);
  const [modal, setModal] = useState(null); // { type: 'review'|'return', order }
  const [actionError, setActionError] = useState('');
  const { data, loading, error, reload } = useAsync(
    () => orderApi.mine({ ...filters, page, page_size: 8 }),
    [filters, page],
  );

  const cancel = async (order) => {
    if (!window.confirm(`Cancel order #${order.id}?`)) return;
    setActionError('');
    try {
      await orderApi.cancel(order.id);
      reload();
    } catch (e) {
      setActionError(errorMessage(e));
    }
  };

  const activeCount = data?.items.filter((o) => ACTIVE.includes(o.status)).length ?? 0;

  return (
    <div className="container page">
      <div className="page-header">
        <div>
          <h1>My orders</h1>
          <p className="muted">{activeCount ? `${activeCount} active order(s) on this page` : 'Track, review and manage your orders.'}</p>
        </div>
        <Link to="/insights" className="btn btn-ghost">✨ AI insights</Link>
      </div>
      <OrderFilters filters={filters} onChange={(f) => { setFilters(f); setPage(1); }} />
      <ErrorMessage message={error || actionError} onRetry={error ? reload : undefined} />
      {loading && !data ? (
        <Loader />
      ) : data?.items.length === 0 ? (
        <p className="empty">No orders found. <Link to="/restaurants">Order something tasty!</Link></p>
      ) : (
        <div className="order-list">
          {data?.items.map((o) => {
            const delivered = o.status === 'DELIVERED';
            return (
              <article key={o.id} className="card order-card">
                <div className="order-card-head">
                  <div>
                    <Link to={`/orders/${o.id}`}><strong>#{o.id} · {o.restaurant_name}</strong></Link>
                    <div className="muted small">{dateTime(o.created_at)}</div>
                  </div>
                  <StatusBadge status={o.status} />
                </div>
                <OrderItemsList items={o.items} />
                <div className="order-meta">
                  <span>Total <strong>{money(o.total_amount)}</strong></span>
                  <span>Payment <StatusBadge kind="payment" status={o.payment_status} /></span>
                  {o.return_status !== 'none' && <span>Return <StatusBadge kind="return" status={o.return_status} /></span>}
                </div>
                <div className="actions">
                  <Link to={`/orders/${o.id}`} className="btn btn-sm btn-ghost">Track</Link>
                  {o.status === 'PLACED' && (
                    <button className="btn btn-sm btn-danger" onClick={() => cancel(o)}>Cancel</button>
                  )}
                  {delivered && !o.has_review && (
                    <button className="btn btn-sm" onClick={() => setModal({ type: 'review', order: o })}>Review</button>
                  )}
                  {delivered && o.return_status === 'none' && (
                    <button className="btn btn-sm btn-ghost" onClick={() => setModal({ type: 'return', order: o })}>Request refund</button>
                  )}
                </div>
              </article>
            );
          })}
        </div>
      )}
      {data && <Pagination page={data.page} pages={data.pages} total={data.total} onChange={setPage} />}
      {modal?.type === 'review' && <ReviewModal order={modal.order} onClose={() => setModal(null)} onDone={reload} />}
      {modal?.type === 'return' && <ReturnModal order={modal.order} onClose={() => setModal(null)} onDone={reload} />}
    </div>
  );
}
