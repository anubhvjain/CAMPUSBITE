import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { orderApi } from '../api';
import { errorMessage } from '../api/client';
import ErrorMessage from '../components/ErrorMessage';
import { useAuth } from '../context/AuthContext';
import { useCart } from '../context/CartContext';
import { money } from '../utils';

export default function Cart() {
  const { user } = useAuth();
  const { cart, updateQuantity, removeItem, clear, total } = useCart();
  const navigate = useNavigate();
  const [address, setAddress] = useState(user?.address || '');
  const [notes, setNotes] = useState('');
  const [card, setCard] = useState({ number: '4242 4242 4242 4242', name: user?.name || '' });
  const [error, setError] = useState('');
  const [placing, setPlacing] = useState(false);

  if (!cart.items.length) {
    return (
      <div className="container page center">
        <h1>Your cart is empty</h1>
        <p className="muted">Browse restaurants and add some dishes.</p>
        <Link to="/restaurants" className="btn">Find food</Link>
      </div>
    );
  }

  const checkout = async (e) => {
    e.preventDefault();
    setError('');
    setPlacing(true);
    try {
      const order = await orderApi.place({
        restaurant_id: cart.restaurant.id,
        items: cart.items.map((i) => ({ menu_item_id: i.id, quantity: i.quantity })),
        delivery_address: address,
        notes: notes || null,
        payment_method: 'dummy_card',
      });
      clear();
      navigate(`/orders/${order.id}`, { state: { justPlaced: true } });
    } catch (err) {
      setError(errorMessage(err, 'Could not place order'));
    } finally {
      setPlacing(false);
    }
  };

  return (
    <div className="container page">
      <h1>Your cart</h1>
      <p className="muted">From <Link to={`/restaurants/${cart.restaurant.id}`}>{cart.restaurant.name}</Link></p>
      <div className="two-col">
        <div className="card card-body">
          <ul className="cart-items">
            {cart.items.map((i) => (
              <li key={i.id}>
                <div>
                  <strong>{i.name}</strong>
                  <div className="muted small">{money(i.price)} each</div>
                </div>
                <div className="qty">
                  <button className="icon-btn" onClick={() => updateQuantity(i.id, i.quantity - 1)} aria-label="Decrease">−</button>
                  <span>{i.quantity}</span>
                  <button className="icon-btn" onClick={() => updateQuantity(i.id, i.quantity + 1)} aria-label="Increase">+</button>
                </div>
                <strong>{money(i.price * i.quantity)}</strong>
                <button className="btn btn-sm btn-ghost" onClick={() => removeItem(i.id)}>Remove</button>
              </li>
            ))}
          </ul>
          <div className="cart-total">
            <span>Total</span>
            <strong>{money(total)}</strong>
          </div>
          <button className="btn btn-sm btn-ghost" onClick={clear}>Clear cart</button>
        </div>

        <form className="card card-body checkout" onSubmit={checkout}>
          <h2>Checkout</h2>
          <ErrorMessage message={error} />
          <label>
            Delivery address
            <input required minLength={3} value={address} onChange={(e) => setAddress(e.target.value)} />
          </label>
          <label>
            Notes for the restaurant
            <textarea rows={2} value={notes} onChange={(e) => setNotes(e.target.value)} placeholder="Less spicy, no onions…" />
          </label>
          <fieldset className="dummy-payment">
            <legend>💳 Dummy payment</legend>
            <p className="muted small">No real payment is taken. Any values work.</p>
            <label>
              Card number
              <input value={card.number} onChange={(e) => setCard({ ...card, number: e.target.value })} />
            </label>
            <label>
              Name on card
              <input value={card.name} onChange={(e) => setCard({ ...card, name: e.target.value })} />
            </label>
          </fieldset>
          <button className="btn btn-block" disabled={placing}>
            {placing ? 'Processing payment…' : `Pay ${money(total)} & place order`}
          </button>
        </form>
      </div>
    </div>
  );
}
