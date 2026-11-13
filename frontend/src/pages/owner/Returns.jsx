import { useState } from 'react';
import { Link } from 'react-router-dom';
import { ownerApi } from '../../api';
import { errorMessage } from '../../api/client';
import ErrorMessage from '../../components/ErrorMessage';
import Loader from '../../components/Loader';
import Pagination from '../../components/Pagination';
import StatusBadge from '../../components/StatusBadge';
import { useAsync } from '../../hooks';
import { dateTime, money } from '../../utils';

export default function Returns() {
  const [status, setStatus] = useState('requested');
  const [page, setPage] = useState(1);
  const [notes, setNotes] = useState({});
  const [actionError, setActionError] = useState('');
  const { data, loading, error, reload } = useAsync(() => ownerApi.returns({ status, page, page_size: 10 }), [status, page]);

  const decide = async (r, approve) => {
    const verb = approve ? 'Approve and refund' : 'Reject';
    if (!window.confirm(`${verb} return for order #${r.order_id}?`)) return;
    setActionError('');
    try {
      await (approve ? ownerApi.approveReturn : ownerApi.rejectReturn)(r.id, notes[r.id] || null);
      reload();
    } catch (e) {
      setActionError(errorMessage(e));
    }
  };

  return (
    <div className="container page">
      <div className="page-header">
        <h1>Return & refund requests</h1>
        <div className="tabs">
          {[['requested', 'Pending'], ['approved', 'Approved'], ['rejected', 'Rejected'], ['', 'All']].map(([v, l]) => (
            <button key={l} className={`tab ${status === v ? 'active' : ''}`} onClick={() => { setStatus(v); setPage(1); }}>{l}</button>
          ))}
        </div>
      </div>
      <ErrorMessage message={error || actionError} onRetry={error ? reload : undefined} />
      {loading && !data ? (
        <Loader />
      ) : data?.items.length === 0 ? (
        <p className="empty">No requests here.</p>
      ) : (
        <div className="order-list">
          {data?.items.map((r) => (
            <article key={r.id} className="card order-card">
              <div className="order-card-head">
                <div>
                  <Link to={`/orders/${r.order_id}`}><strong>Order #{r.order_id}</strong></Link>
                  <div className="muted small">{r.customer_name} · {dateTime(r.created_at)} · {money(r.order_total)}</div>
                </div>
                <StatusBadge kind="return" status={r.status} />
              </div>
              <p><strong>Reason:</strong> {r.reason}</p>
              {r.resolution_note && <p className="muted small">Note: {r.resolution_note}</p>}
              {r.status === 'requested' && (
                <div className="actions">
                  <input placeholder="Optional note to customer" value={notes[r.id] || ''}
                    onChange={(e) => setNotes({ ...notes, [r.id]: e.target.value })} />
                  <button className="btn btn-sm" onClick={() => decide(r, true)}>Approve & refund</button>
                  <button className="btn btn-sm btn-danger" onClick={() => decide(r, false)}>Reject</button>
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
