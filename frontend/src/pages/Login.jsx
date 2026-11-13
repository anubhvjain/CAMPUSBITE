import { useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { errorMessage } from '../api/client';
import ErrorMessage from '../components/ErrorMessage';
import { ROLE_HOME, useAuth } from '../context/AuthContext';

const DEMO = [
  ['Customer', 'customer@campusbite.com'],
  ['Owner', 'owner@campusbite.com'],
  ['Delivery', 'partner@campusbite.com'],
];

export default function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [form, setForm] = useState({ email: '', password: '' });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const user = await login(form.email, form.password);
      const from = location.state?.from;
      navigate(from && from !== '/login' ? from : ROLE_HOME[user.role], { replace: true });
    } catch (err) {
      setError(errorMessage(err, 'Login failed'));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-page">
      <form className="card auth-card" onSubmit={submit}>
        <h1>Welcome back</h1>
        <p className="muted">Log in to continue to CampusBite</p>
        <ErrorMessage message={error} />
        <label>
          Email
          <input type="email" required autoComplete="email" value={form.email}
            onChange={(e) => setForm({ ...form, email: e.target.value })} />
        </label>
        <label>
          Password
          <input type="password" required autoComplete="current-password" value={form.password}
            onChange={(e) => setForm({ ...form, password: e.target.value })} />
        </label>
        <button className="btn btn-block" disabled={loading}>
          {loading ? 'Logging in…' : 'Log in'}
        </button>
        <p className="muted center">
          New here? <Link to="/register">Create an account</Link>
        </p>
        <div className="demo-box">
          <span className="muted small">Demo accounts (password: password123)</span>
          <div className="chips">
            {DEMO.map(([name, email]) => (
              <button type="button" key={email} className="chip"
                onClick={() => setForm({ email, password: 'password123' })}>
                {name}
              </button>
            ))}
          </div>
        </div>
      </form>
    </div>
  );
}
