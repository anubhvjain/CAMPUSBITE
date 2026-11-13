import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { errorMessage } from '../api/client';
import ErrorMessage from '../components/ErrorMessage';
import { ROLE_HOME, useAuth } from '../context/AuthContext';

const ROLES = [
  ['customer', 'Customer'],
  ['restaurant_owner', 'Restaurant Owner'],
  ['delivery_partner', 'Delivery Partner'],
];

export default function Register() {
  const { register } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState({
    name: '', email: '', password: '', role: 'customer', phone: '', address: '', restaurant_name: '',
  });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });

  const submit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const body = Object.fromEntries(Object.entries(form).filter(([, v]) => v !== ''));
      const user = await register(body);
      navigate(ROLE_HOME[user.role], { replace: true });
    } catch (err) {
      setError(errorMessage(err, 'Registration failed'));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-page">
      <form className="card auth-card" onSubmit={submit}>
        <h1>Create account</h1>
        <ErrorMessage message={error} />
        <label>
          I am a
          <select value={form.role} onChange={set('role')}>
            {ROLES.map(([v, l]) => (
              <option key={v} value={v}>{l}</option>
            ))}
          </select>
        </label>
        <label>
          Full name
          <input required minLength={2} value={form.name} onChange={set('name')} />
        </label>
        <label>
          Email
          <input type="email" required value={form.email} onChange={set('email')} />
        </label>
        <label>
          Password
          <input type="password" required minLength={6} maxLength={72} value={form.password} onChange={set('password')} />
        </label>
        <label>
          Phone
          <input value={form.phone} onChange={set('phone')} />
        </label>
        {form.role !== 'delivery_partner' && (
          <label>
            {form.role === 'customer' ? 'Delivery address' : 'Restaurant address'}
            <input value={form.address} onChange={set('address')} />
          </label>
        )}
        {form.role === 'restaurant_owner' && (
          <label>
            Restaurant name
            <input required value={form.restaurant_name} onChange={set('restaurant_name')} />
          </label>
        )}
        <button className="btn btn-block" disabled={loading}>
          {loading ? 'Creating…' : 'Sign up'}
        </button>
        <p className="muted center">
          Already registered? <Link to="/login">Log in</Link>
        </p>
      </form>
    </div>
  );
}
