import { useState } from 'react';
import { ownerApi } from '../../api';
import { errorMessage } from '../../api/client';
import ErrorMessage from '../../components/ErrorMessage';
import Loader from '../../components/Loader';
import Modal from '../../components/Modal';
import Pagination from '../../components/Pagination';
import { useAsync, useDebounced } from '../../hooks';
import { money } from '../../utils';

const EMPTY = { name: '', description: '', price: '', category: '', image_url: '', is_available: true };

function DishForm({ initial, onClose, onSaved }) {
  const [form, setForm] = useState({ ...EMPTY, ...initial, price: initial?.price ?? '' });
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.type === 'checkbox' ? e.target.checked : e.target.value });

  const submit = async (e) => {
    e.preventDefault();
    setSaving(true);
    setError('');
    const body = {
      name: form.name,
      description: form.description || null,
      price: Number(form.price).toFixed(2),
      category: form.category || null,
      image_url: form.image_url || null,
      is_available: form.is_available,
    };
    try {
      if (initial?.id) await ownerApi.updateItem(initial.id, body);
      else await ownerApi.createItem(body);
      onSaved();
      onClose();
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setSaving(false);
    }
  };

  return (
    <Modal title={initial?.id ? 'Edit dish' : 'Add dish'} onClose={onClose}>
      <form className="form" onSubmit={submit}>
        <ErrorMessage message={error} />
        <label>Name<input required value={form.name} onChange={set('name')} /></label>
        <label>Price (₹)<input required type="number" min="1" step="0.01" value={form.price} onChange={set('price')} /></label>
        <label>Category<input value={form.category || ''} onChange={set('category')} placeholder="Mains, Desserts…" /></label>
        <label>Description<textarea rows={2} value={form.description || ''} onChange={set('description')} /></label>
        <label>Image URL<input value={form.image_url || ''} onChange={set('image_url')} /></label>
        <label className="checkbox"><input type="checkbox" checked={form.is_available} onChange={set('is_available')} /> Available</label>
        <button className="btn btn-block" disabled={saving}>{saving ? 'Saving…' : 'Save'}</button>
      </form>
    </Modal>
  );
}

export default function MenuManagement() {
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(1);
  const [editing, setEditing] = useState(null); // null | {} (new) | dish
  const [actionError, setActionError] = useState('');
  const q = useDebounced(search);
  const { data, loading, error, reload } = useAsync(() => ownerApi.menu({ search: q, page, page_size: 15 }), [q, page]);

  const act = async (fn) => {
    setActionError('');
    try {
      await fn();
      reload();
    } catch (e) {
      setActionError(errorMessage(e));
    }
  };

  return (
    <div className="container page">
      <div className="page-header">
        <h1>Menu management</h1>
        <div className="actions">
          <input className="search" placeholder="Search dishes…" value={search} onChange={(e) => { setSearch(e.target.value); setPage(1); }} />
          <button className="btn" onClick={() => setEditing({})}>+ Add dish</button>
        </div>
      </div>
      <ErrorMessage message={error || actionError} onRetry={error ? reload : undefined} />
      {loading && !data ? (
        <Loader />
      ) : data?.items.length === 0 ? (
        <p className="empty">No dishes yet. Add your first one!</p>
      ) : (
        <div className="table-wrap card">
          <table className="table">
            <thead>
              <tr><th>Dish</th><th>Category</th><th>Price</th><th>Available</th><th /></tr>
            </thead>
            <tbody>
              {data?.items.map((d) => (
                <tr key={d.id} className={d.is_available ? '' : 'row-muted'}>
                  <td data-label="Dish"><strong>{d.name}</strong><div className="muted small">{d.description}</div></td>
                  <td data-label="Category">{d.category || '—'}</td>
                  <td data-label="Price">{money(d.price)}</td>
                  <td data-label="Available">
                    <label className="switch">
                      <input type="checkbox" checked={d.is_available}
                        onChange={(e) => act(() => ownerApi.setAvailability(d.id, e.target.checked))} />
                      <span>{d.is_available ? 'Yes' : 'No'}</span>
                    </label>
                  </td>
                  <td className="actions">
                    <button className="btn btn-sm btn-ghost" onClick={() => setEditing(d)}>Edit</button>
                    <button className="btn btn-sm btn-danger"
                      onClick={() => window.confirm(`Delete ${d.name}?`) && act(() => ownerApi.deleteItem(d.id))}>
                      Delete
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {data && <Pagination page={data.page} pages={data.pages} total={data.total} onChange={setPage} />}
      {editing && <DishForm initial={editing} onClose={() => setEditing(null)} onSaved={reload} />}
    </div>
  );
}
