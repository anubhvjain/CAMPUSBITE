import { useState } from 'react';
import { Link } from 'react-router-dom';
import { restaurantApi } from '../api';
import ErrorMessage from '../components/ErrorMessage';
import Loader from '../components/Loader';
import Pagination from '../components/Pagination';
import { useAsync, useDebounced } from '../hooks';

export default function Restaurants() {
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(1);
  const q = useDebounced(search);
  const { data, loading, error, reload } = useAsync(() => restaurantApi.list({ search: q, page, page_size: 12 }), [q, page]);

  return (
    <div className="container page">
      <div className="page-header">
        <div>
          <h1>Restaurants near campus</h1>
          <p className="muted">Pick a place and start building your order.</p>
        </div>
        <input className="search" placeholder="Search by name or cuisine…" value={search}
          onChange={(e) => { setSearch(e.target.value); setPage(1); }} />
      </div>
      <ErrorMessage message={error} onRetry={reload} />
      {loading && !data ? (
        <Loader />
      ) : data?.items.length === 0 ? (
        <p className="empty">No restaurants match your search.</p>
      ) : (
        <div className="grid">
          {data?.items.map((r) => (
            <Link key={r.id} to={`/restaurants/${r.id}`} className="card restaurant-card">
              <div className="restaurant-img" style={{ backgroundImage: r.image_url ? `url(${r.image_url})` : undefined }}>
                {!r.image_url && <span>🍽️</span>}
              </div>
              <div className="card-body">
                <h3>{r.name}</h3>
                <p className="muted small">{r.cuisine || 'Assorted'} · {r.address || 'On campus'}</p>
                <p className="small">
                  {r.avg_rating ? `⭐ ${r.avg_rating.toFixed(1)} (${r.review_count})` : 'No ratings yet'}
                </p>
              </div>
            </Link>
          ))}
        </div>
      )}
      {data && <Pagination page={data.page} pages={data.pages} total={data.total} onChange={setPage} />}
    </div>
  );
}
