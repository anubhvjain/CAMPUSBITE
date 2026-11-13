import { createContext, useContext, useEffect, useMemo, useState } from 'react';

const CART_KEY = 'campusbite_cart';
const CartContext = createContext(null);
const emptyCart = { restaurant: null, items: [] };

function readCart() {
  try {
    return JSON.parse(localStorage.getItem(CART_KEY)) || emptyCart;
  } catch {
    return emptyCart;
  }
}

export function CartProvider({ children }) {
  const [cart, setCart] = useState(readCart);

  useEffect(() => {
    localStorage.setItem(CART_KEY, JSON.stringify(cart));
  }, [cart]);

  const value = useMemo(() => {
    /** Returns false if the dish is from another restaurant and the caller must confirm a reset. */
    const addItem = (restaurant, dish, { force = false } = {}) => {
      if (cart.restaurant && cart.restaurant.id !== restaurant.id && !force) return false;
      setCart((prev) => {
        const base = prev.restaurant && prev.restaurant.id !== restaurant.id ? emptyCart : prev;
        const existing = base.items.find((i) => i.id === dish.id);
        const items = existing
          ? base.items.map((i) => (i.id === dish.id ? { ...i, quantity: Math.min(i.quantity + 1, 50) } : i))
          : [...base.items, { id: dish.id, name: dish.name, price: Number(dish.price), quantity: 1 }];
        return { restaurant: { id: restaurant.id, name: restaurant.name }, items };
      });
      return true;
    };
    const updateQuantity = (id, quantity) =>
      setCart((prev) => {
        const items =
          quantity <= 0
            ? prev.items.filter((i) => i.id !== id)
            : prev.items.map((i) => (i.id === id ? { ...i, quantity: Math.min(quantity, 50) } : i));
        return items.length ? { ...prev, items } : emptyCart;
      });
    const removeItem = (id) => updateQuantity(id, 0);
    const clear = () => setCart(emptyCart);
    const count = cart.items.reduce((s, i) => s + i.quantity, 0);
    const total = cart.items.reduce((s, i) => s + i.quantity * i.price, 0);
    return { cart, addItem, updateQuantity, removeItem, clear, count, total };
  }, [cart]);

  return <CartContext.Provider value={value}>{children}</CartContext.Provider>;
}

export const useCart = () => useContext(CartContext);
