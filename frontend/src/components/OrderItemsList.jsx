import { money } from '../utils';

export default function OrderItemsList({ items }) {
  return (
    <ul className="order-items">
      {items.map((i) => (
        <li key={i.id}>
          <span>
            {i.quantity} × {i.name}
          </span>
          <span>{money(i.unit_price * i.quantity)}</span>
        </li>
      ))}
    </ul>
  );
}
