import client, { cleanParams } from './client';

const data = (p) => p.then((r) => r.data);

export const authApi = {
  login: (body) => data(client.post('/auth/login', body)),
  register: (body) => data(client.post('/auth/register', body)),
  me: () => data(client.get('/auth/me')),
};

export const restaurantApi = {
  list: (params) => data(client.get('/restaurants', { params: cleanParams(params) })),
  get: (id) => data(client.get(`/restaurants/${id}`)),
  menu: (id, params) => data(client.get(`/restaurants/${id}/menu`, { params: cleanParams(params) })),
  reviews: (id, params) => data(client.get(`/restaurants/${id}/reviews`, { params })),
};

export const orderApi = {
  place: (body) => data(client.post('/orders', body)),
  mine: (params) => data(client.get('/orders/my', { params: cleanParams(params) })),
  get: (id) => data(client.get(`/orders/${id}`)),
  cancel: (id) => data(client.post(`/orders/${id}/cancel`)),
  review: (id, body) => data(client.post(`/orders/${id}/review`, body)),
  requestReturn: (id, body) => data(client.post(`/orders/${id}/return`, body)),
};

export const ownerApi = {
  restaurant: () => data(client.get('/owner/restaurant')),
  updateRestaurant: (body) => data(client.put('/owner/restaurant', body)),
  menu: (params) => data(client.get('/owner/menu', { params: cleanParams(params) })),
  createItem: (body) => data(client.post('/owner/menu', body)),
  updateItem: (id, body) => data(client.put(`/owner/menu/${id}`, body)),
  setAvailability: (id, isAvailable) =>
    data(client.patch(`/owner/menu/${id}/availability`, { is_available: isAvailable })),
  deleteItem: (id) => data(client.delete(`/owner/menu/${id}`)),
  orders: (params) => data(client.get('/owner/orders', { params: cleanParams(params) })),
  updateStatus: (id, status) => data(client.patch(`/owner/orders/${id}/status`, { status })),
  partners: () => data(client.get('/owner/delivery-partners')),
  assign: (id, partnerId) => data(client.post(`/owner/orders/${id}/assign`, { delivery_partner_id: partnerId })),
  stats: () => data(client.get('/owner/stats')),
  returns: (params) => data(client.get('/owner/returns', { params: cleanParams(params) })),
  approveReturn: (id, note) => data(client.post(`/owner/returns/${id}/approve`, { note })),
  rejectReturn: (id, note) => data(client.post(`/owner/returns/${id}/reject`, { note })),
  reminders: (params) => data(client.get('/owner/reminders', { params })),
  refreshReminders: () => data(client.post('/owner/reminders/refresh')),
  dismissReminder: (id) => data(client.post(`/owner/reminders/${id}/dismiss`)),
};

export const deliveryApi = {
  orders: (params) => data(client.get('/delivery/orders', { params: cleanParams(params) })),
  history: (params) => data(client.get('/delivery/history', { params })),
  updateStatus: (id, status) => data(client.patch(`/delivery/orders/${id}/status`, { status })),
};

export const aiApi = {
  insights: (question) => data(client.post('/ai/insights', { question: question || null })),
};
