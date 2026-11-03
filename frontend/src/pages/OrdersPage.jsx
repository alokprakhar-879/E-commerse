import React, { useState, useEffect } from 'react';
import { api } from '../api';

export default function OrdersPage() {
  const [orders, setOrders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(null);
  const [message, setMessage] = useState(null);

  useEffect(() => {
    loadOrders();
  }, []);

  const loadOrders = async () => {
    setLoading(true);
    try {
      const data = await api.getOrders();
      setOrders(data);
    } catch (err) {
      console.error('Failed to load orders', err);
    } finally {
      setLoading(false);
    }
  };

  const handleCancelOrder = async (orderId) => {
    if (!window.confirm(`Are you sure you want to cancel Order #${orderId}? Stock will be automatically restored.`)) {
      return;
    }

    setActionLoading(orderId);
    setMessage(null);

    try {
      const updated = await api.cancelOrder(orderId);
      setMessage({
        type: 'success',
        text: `Order #${orderId} was cancelled. Inventory was restored and payment marked as REFUNDED.`
      });
      setOrders((prev) => prev.map((o) => (o.id === orderId ? updated : o)));
    } catch (err) {
      setMessage({
        type: 'danger',
        text: err.message || `Failed to cancel Order #${orderId}`
      });
    } finally {
      setActionLoading(null);
    }
  };

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">Orders Management</h1>
          <p className="page-subtitle">Track historical orders, view transaction logs, and test atomic order cancellation</p>
        </div>
        <button className="btn btn-outline" onClick={loadOrders}>
          ↻ Refresh Orders
        </button>
      </div>

      {message && (
        <div className={`alert-banner alert-${message.type}`}>
          <span>{message.text}</span>
          <button className="btn btn-sm btn-outline" onClick={() => setMessage(null)}>✕</button>
        </div>
      )}

      {loading ? (
        <p>Loading orders from database...</p>
      ) : orders.length === 0 ? (
        <div className="alert-banner alert-info">
          No orders have been placed yet.
        </div>
      ) : (
        <div className="table-wrapper">
          <table className="data-table">
            <thead>
              <tr>
                <th>Order ID</th>
                <th>Customer</th>
                <th>Date & Time</th>
                <th>Items Ordered</th>
                <th>Total Amount</th>
                <th>Status</th>
                <th>Payment</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {orders.map((o) => {
                const isCancelled = o.order_status === 'CANCELLED';
                const createdDate = o.created_at ? new Date(o.created_at).toLocaleString() : 'N/A';
                const latestPayment = o.payments && o.payments.length > 0 ? o.payments[o.payments.length - 1] : null;

                return (
                  <tr key={o.id}>
                    <td>
                      <strong>#{o.id}</strong>
                    </td>
                    <td>
                      <div><strong>{o.customer_name || 'Customer #' + o.customer_id}</strong></div>
                      <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>{o.customer_email}</div>
                    </td>
                    <td style={{ fontSize: '0.85rem', color: '#475569' }}>
                      {createdDate}
                    </td>
                    <td>
                      <ul style={{ listStyle: 'none', padding: 0, margin: 0, fontSize: '0.85rem' }}>
                        {o.items.map((it) => (
                          <li key={it.id}>
                            {it.quantity}x {it.product_name} (${parseFloat(it.unit_price).toFixed(2)})
                          </li>
                        ))}
                      </ul>
                    </td>
                    <td>
                      <strong>${parseFloat(o.total_amount).toFixed(2)}</strong>
                    </td>
                    <td>
                      <span className={`status-badge status-${o.order_status}`}>
                        {o.order_status}
                      </span>
                    </td>
                    <td>
                      {latestPayment ? (
                        <span style={{ fontSize: '0.8rem' }}>
                          <strong>{latestPayment.payment_status}</strong> via {latestPayment.payment_method}
                        </span>
                      ) : (
                        <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>No record</span>
                      )}
                    </td>
                    <td>
                      {!isCancelled && (
                        <button
                          className="btn btn-sm btn-danger"
                          disabled={actionLoading === o.id}
                          onClick={() => handleCancelOrder(o.id)}
                        >
                          {actionLoading === o.id ? 'Rolling back...' : 'Cancel Order'}
                        </button>
                      )}
                      {isCancelled && (
                        <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
                          Restored
                        </span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
