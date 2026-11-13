import { Navigate, Route, Routes } from 'react-router-dom';
import Navbar from './components/Navbar';
import ProtectedRoute from './components/ProtectedRoute';
import { ROLE_HOME, useAuth } from './context/AuthContext';
import Cart from './pages/Cart';
import Login from './pages/Login';
import NotFound from './pages/NotFound';
import Register from './pages/Register';
import RestaurantMenu from './pages/RestaurantMenu';
import Restaurants from './pages/Restaurants';
import AIInsights from './pages/customer/AIInsights';
import CustomerDashboard from './pages/customer/CustomerDashboard';
import OrderDetail from './pages/customer/OrderDetail';
import DeliveryDashboard from './pages/delivery/DeliveryDashboard';
import DeliveryHistory from './pages/delivery/DeliveryHistory';
import MenuManagement from './pages/owner/MenuManagement';
import OrderManagement from './pages/owner/OrderManagement';
import OwnerDashboard from './pages/owner/OwnerDashboard';
import Returns from './pages/owner/Returns';

function Home() {
  const { user } = useAuth();
  return <Navigate to={user ? ROLE_HOME[user.role] : '/restaurants'} replace />;
}

function GuestOnly({ children }) {
  const { user } = useAuth();
  return user ? <Navigate to={ROLE_HOME[user.role]} replace /> : children;
}

export default function App() {
  return (
    <>
      <Navbar />
      <main>
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/login" element={<GuestOnly><Login /></GuestOnly>} />
          <Route path="/register" element={<GuestOnly><Register /></GuestOnly>} />
          <Route path="/restaurants" element={<Restaurants />} />
          <Route path="/restaurants/:id" element={<RestaurantMenu />} />

          <Route element={<ProtectedRoute roles={['customer']} />}>
            <Route path="/cart" element={<Cart />} />
            <Route path="/dashboard" element={<CustomerDashboard />} />
            <Route path="/insights" element={<AIInsights />} />
          </Route>

          <Route element={<ProtectedRoute />}>
            <Route path="/orders/:id" element={<OrderDetail />} />
          </Route>

          <Route element={<ProtectedRoute roles={['restaurant_owner']} />}>
            <Route path="/owner" element={<OwnerDashboard />} />
            <Route path="/owner/orders" element={<OrderManagement />} />
            <Route path="/owner/menu" element={<MenuManagement />} />
            <Route path="/owner/returns" element={<Returns />} />
          </Route>

          <Route element={<ProtectedRoute roles={['delivery_partner']} />}>
            <Route path="/delivery" element={<DeliveryDashboard />} />
            <Route path="/delivery/history" element={<DeliveryHistory />} />
          </Route>

          <Route path="*" element={<NotFound />} />
        </Routes>
      </main>
    </>
  );
}
