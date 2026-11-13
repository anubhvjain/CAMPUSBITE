import { useState } from 'react';
import { deliveryApi } from '../../api';
import ErrorMessage from '../../components/ErrorMessage';
import Loader from '../../components/Loader';
import Pagination from '../../components/Pagination';
import StatusBadge from '../../components/StatusBadge';
import { useAsync } from '../../hooks';
import { dateTime, money } from '../../utils';

export default function DeliveryHistory() {
  const [page, setPage] = useState(1);
  const { data, loading, error, reload } = useAsync(() => deliveryApi.history({ page, page_size: 10 }), [page]);

  return (
    <div className="container page">
      <h1>Delivery history</h1>
      <ErrorMessage message={error} onRetry={reload} />
      {loading && !data ? (
        <Loader />
      ) : data?.items.length === 0 ? (
        <p className="empty">No completed deliveries yet.</p>
      ) : (
        <div className="table-wrap card">
          <table className="table">
            <thead>
              <tr><th>Order</th><th>Restaurant</th><th>Customer</th><th>Address</th><th>Total</th><th>Status</th><th>Completed</th></tr>
            </thead>
            <tbody>
              {data?.items.map((o) => (
                <tr key={o.id}>
                  <td data-label="Order">#{o.id}</td>
                  <td data-label="Restaurant">{o.restaurant_name}</td>
                  <td data-label="Customer">{o.customer?.name}</td>
                  <td data-label="Address">{o.delivery_address}</td>
                  <td data-label="Total">{money(o.total_amount)}</td>
                  <td data-label="Status"><StatusBadge status={o.status} /></td>
                  <td data-label="Completed">{dateTime(o.updated_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {data && <Pagination page={data.page} pages={data.pages} total={data.total} onChange={setPage} />}
    </div>
  );
}
