import { useState } from 'react';
import { Link, NavLink, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { useCart } from '../context/CartContext';

const LINKS = {
  customer: [
    ['/restaurants', 'Restaurants'],
    ['/dashboard', 'My Orders'],
    ['/insights', 'AI Insights'],
  ],
  restaurant_owner: [
    ['/owner', 'Dashboard'],
    ['/owner/orders', 'Orders'],
    ['/owner/menu', 'Menu'],
    ['/owner/returns', 'Returns'],
  ],
  delivery_partner: [
    ['/delivery', 'Deliveries'],
    ['/delivery/history', 'History'],
  ],
};

export default function Navbar() {
  const { user, logout } = useAuth();
  const { count } = useCart();
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);
  const links = user ? LINKS[user.role] : [['/restaurants', 'Restaurants']];

  const close = () => setOpen(false);
  const handleLogout = () => {
    logout();
    close();
    navigate('/login');
  };

  return (
    <header className="navbar">
      <div className="container navbar-inner">
        <Link to="/" className="brand" onClick={close}>
          🍔 Campus<span>Bite</span>
        </Link>
        <button className="menu-toggle" aria-label="Toggle menu" onClick={() => setOpen((o) => !o)}>
          ☰
        </button>
        <nav className={`nav-links ${open ? 'open' : ''}`}>
          {links.map(([to, text]) => (
            <NavLink key={to} to={to} end onClick={close}>
              {text}
            </NavLink>
          ))}
          {user?.role === 'customer' && (
            <NavLink to="/cart" onClick={close} className="cart-link">
              🛒 Cart{count > 0 && <span className="cart-count">{count}</span>}
            </NavLink>
          )}
          {user ? (
            <div className="nav-user">
              <span className="muted">Hi, {user.name.split(' ')[0]}</span>
              <button className="btn btn-sm btn-ghost" onClick={handleLogout}>
                Logout
              </button>
            </div>
          ) : (
            <>
              <NavLink to="/login" onClick={close}>
                Login
              </NavLink>
              <Link to="/register" className="btn btn-sm" onClick={close}>
                Sign up
              </Link>
            </>
          )}
        </nav>
      </div>
    </header>
  );
}
