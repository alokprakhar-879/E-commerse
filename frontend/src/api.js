// Base API URL pointing to the FastAPI backend
const API_BASE = 'http://localhost:8000';

async function request(endpoint, options = {}) {
  const url = `${API_BASE}${endpoint}`;
  const config = {
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
    ...options,
  };

  try {
    const res = await fetch(url, config);

    if (res.status === 204) {
      return null;
    }

    const data = await res.json();
    if (!res.ok) {
      const errorMsg = data.detail || (typeof data === 'string' ? data : 'An error occurred');
      const error = new Error(errorMsg);
      error.status = res.status;
      error.data = data;
      throw error;
    }
    return data;
  } catch (err) {
    if (err.status) throw err;
    throw new Error(`Network connection error: Unable to reach backend at ${API_BASE}`);
  }
}

export const api = {
  // Categories
  getCategories: () => request('/categories'),
  createCategory: (data) => request('/categories', { method: 'POST', body: JSON.stringify(data) }),

  // Products
  getProducts: (categoryId, search) => {
    const params = new URLSearchParams();
    if (categoryId) params.append('category_id', categoryId);
    if (search) params.append('search', search);
    const qs = params.toString() ? `?${params.toString()}` : '';
    return request(`/products${qs}`);
  },
  getProduct: (id) => request(`/products/${id}`),
  createProduct: (data) => request('/products', { method: 'POST', body: JSON.stringify(data) }),
  updateProduct: (id, data) => request(`/products/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  deleteProduct: (id) => request(`/products/${id}`, { method: 'DELETE' }),

  // Customers
  getCustomers: () => request('/customers'),
  createCustomer: (data) => request('/customers', { method: 'POST', body: JSON.stringify(data) }),

  // Orders (ACID transaction)
  getOrders: () => request('/orders'),
  getOrder: (id) => request(`/orders/${id}`),
  placeOrder: (orderData) => request('/orders', { method: 'POST', body: JSON.stringify(orderData) }),
  cancelOrder: (orderId) => request(`/orders/${orderId}/cancel`, { method: 'POST' }),

  // Inventory
  getInventory: () => request('/inventory'),
  getLowStock: () => request('/inventory/low-stock'),
  updateInventory: (productId, data) => request(`/inventory/${productId}`, { method: 'PUT', body: JSON.stringify(data) }),

  // Reports
  getSalesReport: (from, to) => {
    const params = new URLSearchParams();
    if (from) params.append('from', from);
    if (to) params.append('to', to);
    const qs = params.toString() ? `?${params.toString()}` : '';
    return request(`/reports/sales${qs}`);
  },
  getProfitReport: () => request('/reports/profit'),
  getTopProductsReport: (limit = 5) => request(`/reports/top-products?limit=${limit}`)
};
