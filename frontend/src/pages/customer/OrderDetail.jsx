import { useState } from 'react';
import { Link, useLocation, useParams } from 'react-router-dom';
import { orderApi } from '../../api';
import { errorMessage } from '../../api/client';
import ErrorMessage from '../../components/ErrorMessage';
import Loader from '../../components/Loader';
import OrderItemsList from '../../components/OrderItemsList';
import StatusBadge from '../../components/StatusBadge';
import StatusTracker from '../../components/StatusTracker';
import { useAuth } from '../../context/AuthContext';
import { useAsync } from '../../hooks';
import { dateTime, label, money } from '../../utils';
import { ReturnModal, ReviewModal } from './OrderActions';

const BACK = { customer: '/dashboard', restaurant_owner: '/owner/orders', delivery_partner: '/delivery' };

export default function OrderDetail() {
  const { id } = useParams();
  const { user } = useAuth();
  const location = useLocation();
  const { data: o, loading, error, reload } = useAsync(() => orderApi.get(id), [id]);
  const [modal, setModal] = useState(null);
  const [actionError, setActionError] = useState('');

  if (loading && !o) return <Loader />;
  if (error) return <div className="container page"><ErrorMessage message={error} onRetry={reload} /></div>;

  const isCustomer = user.role === 'customer';
  const cancel = async () => {
    if (!window.confirm('Cancel this order?')) return;
    try {
      await orderApi.cancel(o.id);
      reload();
    } catch (e) {
      setActionError(errorMessage(e));
    }
  };

  return (
    <div className="container page narrow">
      <Link to={BACK[user.role]} className="back-link">← Back</Link>
      {location.state?.justPlaced && <div className="alert alert-success">🎉 Order placed! Payment status: mock_paid.</div>}
      <div className="page-header">
        <div>
          <h1>Order #{o.id}</h1>
          <p className="muted">{o.restaurant_name} · {dateTime(o.created_at)}</p>
        </div>
        <button className="btn btn-sm btn-ghost" onClick={reload}>↻ Refresh</button>
      </div>
      <ErrorMessage message={actionError} />
      <div className="card card-body">
        <StatusTracker status={o.status} />
        <p className="muted small">Last updated {dateTime(o.updated_at)}</p>
      </div>
      <div className="two-col">
        <div className="card card-body">
          <h3>Items</h3>
          <OrderItemsList items={o.items} />
          <div className="cart-total"><span>Total</span><strong>{money(o.total_amount)}</strong></div>
          {o.notes && <p className="muted small">Notes: {o.notes}</p>}
        </div>
        <div className="card card-body">
          <h3>Delivery</h3>
          <p>{o.delivery_address}</p>
          {o.delivery_partner && (
            <p className="small">Partner: <strong>{o.delivery_partner.name}</strong> {o.delivery_partner.phone}</p>
          )}
          <h3>Payment</h3>
          <p>Status <StatusBadge kind="payment" status={o.payment_status} /></p>
          <ul className="ledger">
            {o.payments.map((p) => (
              <li key={p.id}>
                <span>{label(p.entry_type)} · {p.reference}</span>
                <span>{p.entry_type === 'refund' ? '−' : ''}{money(p.amount)}</span>
              </li>
            ))}
          </ul>
          {o.return_request && (
            <>
              <h3>Return / refund</h3>
              <p>Status <StatusBadge kind="return" status={o.return_request.status} /></p>
              <p className="small">Reason: {o.return_request.reason}</p>
              {o.return_request.resolution_note && <p className="small">Restaurant: {o.return_request.resolution_note}</p>}
            </>
          )}
          {o.review && (
            <>
              <h3>Your review</h3>
              <p>{'⭐'.repeat(o.review.rating)} {o.review.comment}</p>
            </>
          )}
        </div>
      </div>
      {isCustomer && (
        <div className="actions">
          {o.status === 'PLACED' && <button className="btn btn-danger" onClick={cancel}>Cancel order</button>}
          {o.status === 'DELIVERED' && !o.review && <button className="btn" onClick={() => setModal('review')}>Write a review</button>}
          {o.status === 'DELIVERED' && o.return_status === 'none' && (
            <button className="btn btn-ghost" onClick={() => setModal('return')}>Request return / refund</button>
          )}
        </div>
      )}
      {modal === 'review' && <ReviewModal order={o} onClose={() => setModal(null)} onDone={reload} />}
      {modal === 'return' && <ReturnModal order={o} onClose={() => setModal(null)} onDone={reload} />}
    </div>
  );
}
