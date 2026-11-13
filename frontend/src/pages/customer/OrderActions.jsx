import { useState } from 'react';
import { orderApi } from '../../api';
import { errorMessage } from '../../api/client';
import ErrorMessage from '../../components/ErrorMessage';
import Modal from '../../components/Modal';

export function ReviewModal({ order, onClose, onDone }) {
  const [rating, setRating] = useState(5);
  const [comment, setComment] = useState('');
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setSaving(true);
    setError('');
    try {
      await orderApi.review(order.id, { rating, comment: comment || null });
      onDone?.();
      onClose();
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setSaving(false);
    }
  };

  return (
    <Modal title={`Review order #${order.id}`} onClose={onClose}>
      <form onSubmit={submit} className="form">
        <ErrorMessage message={error} />
        <div className="stars" role="radiogroup" aria-label="Rating">
          {[1, 2, 3, 4, 5].map((n) => (
            <button type="button" key={n} className={n <= rating ? 'star on' : 'star'} onClick={() => setRating(n)}
              aria-label={`${n} star`}>
              ★
            </button>
          ))}
        </div>
        <label>
          Comment
          <textarea rows={3} value={comment} onChange={(e) => setComment(e.target.value)} maxLength={1000} />
        </label>
        <button className="btn btn-block" disabled={saving}>{saving ? 'Submitting…' : 'Submit review'}</button>
      </form>
    </Modal>
  );
}

export function ReturnModal({ order, onClose, onDone }) {
  const [reason, setReason] = useState('');
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setSaving(true);
    setError('');
    try {
      await orderApi.requestReturn(order.id, { reason });
      onDone?.();
      onClose();
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setSaving(false);
    }
  };

  return (
    <Modal title={`Request refund for order #${order.id}`} onClose={onClose}>
      <form onSubmit={submit} className="form">
        <ErrorMessage message={error} />
        <p className="muted small">The restaurant will review your request. Only one request is allowed per order.</p>
        <label>
          Reason
          <textarea rows={4} required minLength={5} maxLength={1000} value={reason} onChange={(e) => setReason(e.target.value)} />
        </label>
        <button className="btn btn-block" disabled={saving}>{saving ? 'Submitting…' : 'Submit request'}</button>
      </form>
    </Modal>
  );
}
