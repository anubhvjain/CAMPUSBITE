import axios from 'axios';

export const TOKEN_KEY = 'campusbite_token';
export const USER_KEY = 'campusbite_user';

const client = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000/api',
  timeout: 45000,
});

client.interceptors.request.use((config) => {
  const token = localStorage.getItem(TOKEN_KEY);
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

client.interceptors.response.use(
  (res) => res,
  (error) => {
    if (error.response?.status === 401 && localStorage.getItem(TOKEN_KEY)) {
      localStorage.removeItem(TOKEN_KEY);
      localStorage.removeItem(USER_KEY);
      window.dispatchEvent(new Event('campusbite:logout'));
    }
    return Promise.reject(error);
  },
);

export function errorMessage(error, fallback = 'Something went wrong') {
  const detail = error?.response?.data?.detail;
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) {
    return detail.map((d) => `${d.loc?.slice(-1)[0] ?? ''}: ${d.msg}`).join('; ');
  }
  if (error?.code === 'ECONNABORTED') return 'Request timed out';
  if (error?.message === 'Network Error') return 'Cannot reach the server';
  return fallback;
}

/** Drop empty values so they don't end up as `?status=` in the query string. */
export const cleanParams = (params) =>
  Object.fromEntries(Object.entries(params).filter(([, v]) => v !== '' && v !== null && v !== undefined));

export default client;
