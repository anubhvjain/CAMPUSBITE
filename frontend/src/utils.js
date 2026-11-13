export const ORDER_STATUSES = [
  'PLACED', 'ACCEPTED', 'PREPARING', 'READY', 'ASSIGNED', 'OUT_FOR_DELIVERY', 'DELIVERED', 'CANCELLED', 'REFUNDED',
];
export const LIFECYCLE = ORDER_STATUSES.slice(0, 7);

export const money = (v) =>
  `₹${Number(v || 0).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

export const dateTime = (v) =>
  v ? new Date(v).toLocaleString('en-IN', { dateStyle: 'medium', timeStyle: 'short' }) : '—';

export const label = (s) => (s ? s.replaceAll('_', ' ').toLowerCase().replace(/^\w/, (c) => c.toUpperCase()) : '');
