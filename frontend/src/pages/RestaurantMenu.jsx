import { useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { restaurantApi } from '../api';
import ErrorMessage from '../components/ErrorMessage';
import Loader from '../components/Loader';
import Pagination from '../components/Pagination';
import { useAuth } from '../context/AuthContext';
import { useCart } from '../context/CartContext';
import { useAsync, useDebounced } from '../hooks';
import { dateTime, money } from '../utils';

export default function RestaurantMenu() {
  const { id } = useParams();
  const { user } = useAuth();
  const { addItem, cart, count, total } = useCart();
  const [filters, setFilters] = useState({ search: '', min_price: '', max_price: '', sort: 'name', available_only: false });
  const [page, setPage] = useState(1);
  const [toast, setToast] = useState('');
  const debounced = useDebounced(filters);

  const restaurant = useAsync(() => restaurantApi.get(id), [id]);
  const menu = useAsync(() => restaurantApi.menu(id, { ...debounced, page, page_size: 24 }), [id, debounced, page]);
  const reviews = useAsync(() => restaurantApi.reviews(id, { page_size: 5 }), [id]);

  const set = (k) => (e) => {
    setFilters({ ...filters, [k]: e.target.type === 'checkbox' ? e.target.checked : e.target.value });
    setPage(1);
  };

  const add = (dish) => {
    const r = restaurant.data;
    if (!addItem(r, dish)) {
      if (!window.confirm(`Your cart has items from ${cart.restaurant.name}. Start a new cart?`)) return;
      addItem(r, dish, { force: true });
    }
    setToast(`Added ${dish.name}`);
    setTimeout(() => setToast(''), 1500);
  };

  if (restaurant.loading && !restaurant.data) return <Loader />;
  if (restaurant.error) return <div className="container page"><ErrorMessage message={restaurant.error} /></div>;
  const r = restaurant.data;
  const canOrder = !user || user.role === 'customer';

  return (
    <div className="container page">
      <Link to="/restaurants" className="back-link">← All restaurants</Link>
      <div className="restaurant-hero card" style={{ backgroundImage: r.image_url ? `linear-gradient(rgba(0,0,0,.45),rgba(0,0,0,.55)),url(${r.image_url})` : undefined }}>
        <h1>{r.name}</h1>
        <p>{r.description}</p>
        <p className="small">{r.cuisine} · {r.address} {r.avg_rating ? `· ⭐ ${r.avg_rating.toFixed(1)} (${r.review_count})` : ''}</p>
      </div>

      <div className="filters">
        <input className="search" placeholder="Search dishes…" value={filters.search} onChange={set('search')} />
        <label>
          Min ₹
          <input type="number" min="0" value={filters.min_price} onChange={set('min_price')} />
        </label>
        <label>
          Max ₹
          <input type="number" min="0" value={filters.max_price} onChange={set('max_price')} />
        </label>
        <label>
          Sort
          <select value={filters.sort} onChange={set('sort')}>
            <option value="name">Name</option>
            <option value="price_asc">Price: low → high</option>
            <option value="price_desc">Price: high → low</option>
          </select>
        </label>
        <label className="checkbox">
          <input type="checkbox" checked={filters.available_only} onChange={set('available_only')} />
          Available only
        </label>
      </div>

      <ErrorMessage message={menu.error} onRetry={menu.reload} />
      {menu.loading && !menu.data ? (
        <Loader />
      ) : menu.data?.items.length === 0 ? (
        <p className="empty">No dishes match these filters.</p>
      ) : (
        <div className="grid dish-grid">
          {menu.data?.items.map((d) => (
            <div key={d.id} className={`card dish-card ${d.is_available ? '' : 'unavailable'}`}>
              <div className="card-body">
                <div className="dish-head">
                  <h3>{d.name}</h3>
                  <strong>{money(d.price)}</strong>
                </div>
                {d.category && <span className="tag">{d.category}</span>}
                <p className="muted small">{d.description}</p>
                {canOrder && (
                  d.is_available ? (
                    user ? (
                      <button className="btn btn-sm" onClick={() => add(d)}>Add to cart</button>
                    ) : (
                      <Link to="/login" className="btn btn-sm btn-ghost">Log in to order</Link>
                    )
                  ) : (
                    <span className="badge badge-order-cancelled">Unavailable</span>
                  )
                )}
              </div>
            </div>
          ))}
        </div>
      )}
      {menu.data && <Pagination page={menu.data.page} pages={menu.data.pages} total={menu.data.total} onChange={setPage} />}

      <section className="section">
        <h2>Recent reviews</h2>
        {reviews.data?.items.length ? (
          <ul className="reviews">
            {reviews.data.items.map((rv) => (
              <li key={rv.id} className="card card-body">
                <strong>{'⭐'.repeat(rv.rating)}</strong> <span className="muted small">— {rv.customer_name}, {dateTime(rv.created_at)}</span>
                {rv.comment && <p>{rv.comment}</p>}
              </li>
            ))}
          </ul>
        ) : (
          <p className="muted">No reviews yet.</p>
        )}
      </section>

      {count > 0 && cart.restaurant?.id === r.id && (
        <Link to="/cart" className="floating-cart">
          🛒 {count} item{count > 1 ? 's' : ''} · {money(total)} — View cart
        </Link>
      )}
      {toast && <div className="toast">{toast}</div>}
    </div>
  );
}
