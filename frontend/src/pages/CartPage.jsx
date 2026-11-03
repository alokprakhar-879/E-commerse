import React, { useState, useEffect } from 'react';
import { api } from '../api';

export default function CartPage({ cart, onUpdateQuantity, onRemoveItem, onClearCart, onOrderPlaced }) {
  const [customers, setCustomers] = useState([]);
  const [selectedCustomerId, setSelectedCustomerId] = useState('');
  const [simulateFailure, setSimulateFailure] = useState(false);
  const [loading, setLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState(null);
  const [successOrder, setSuccessOrder] = useState(null);

  useEffect(() => {
    loadCustomers();
  }, []);

  const loadCustomers = async () => {
    try {
      const data = await api.getCustomers();
      setCustomers(data);
      if (data.length > 0) {
        setSelectedCustomerId(data[0].id);
      }
    } catch (err) {
      console.error('Failed to load customers', err);
    }
  };

  const calculateTotal = () => {
    return cart.reduce((sum, item) => sum + parseFloat(item.product.selling_price) * item.quantity, 0);
  };

  const handlePlaceOrder = async () => {
    setErrorMessage(null);
    setSuccessOrder(null);

    if (cart.length === 0) {
      setErrorMessage('Your cart is empty.');
      return;
    }

    if (!selectedCustomerId) {
      setErrorMessage('Please select a customer for this order.');
      return;
    }

    setLoading(true);

    try {
      const payload = {
        customer_id: parseInt(selectedCustomerId),
        items: cart.map((i) => ({
          product_id: i.product.id,
          quantity: i.quantity,
        })),
        simulate_payment_failure: simulateFailure,
        payment_method: 'CREDIT_CARD',
      };

      const placedOrder = await api.placeOrder(payload);
      setSuccessOrder(placedOrder);
      onClearCart();
      if (onOrderPlaced) onOrderPlaced();
    } catch (err) {
      // Handles 409 Conflict ("Insufficient stock") and 422 Payment Failure
      const detail = err.message || 'Transaction aborted.';
      setErrorMessage(detail);
    } finally {
      setLoading(false);
    }
  };

  if (successOrder) {
    return (
      <div className="cart-items-card" style={{ textAlign: 'center', padding: '3rem 1.5rem' }}>
        <div style={{ fontSize: '3rem', marginBottom: '1rem' }}>🎉</div>
        <h2 style={{ color: 'var(--success)', marginBottom: '0.5rem' }}>Order Placed Successfully!</h2>
        <p style={{ color: 'var(--text-muted)', marginBottom: '1rem' }}>
          Order #{successOrder.id} confirmed with status: <strong>{successOrder.order_status}</strong>
        </p>
        <p style={{ marginBottom: '1.5rem' }}>
          Total Paid: <strong>${parseFloat(successOrder.total_amount).toFixed(2)}</strong> (Payment logged via ACID transaction)
        </p>
        <button className="btn btn-primary" onClick={() => setSuccessOrder(null)}>
          Continue Shopping
        </button>
      </div>
    );
  }

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">Shopping Cart</h1>
          <p className="page-subtitle">Review items, edit quantities, and checkout with ACID concurrency guarantees</p>
        </div>
      </div>

      {errorMessage && (
        <div className="alert-banner alert-danger">
          <div>
            <strong>Transaction Error:</strong> {errorMessage}
          </div>
          <button className="btn btn-sm btn-outline" onClick={() => setErrorMessage(null)}>✕</button>
        </div>
      )}

      {cart.length === 0 ? (
        <div className="cart-items-card" style={{ textAlign: 'center', padding: '3rem' }}>
          <h3>Your cart is empty</h3>
          <p style={{ color: 'var(--text-muted)', margin: '1rem 0' }}>Add some products from the catalog to get started!</p>
        </div>
      ) : (
        <div className="cart-layout">
          {/* Cart Items List */}
          <div className="cart-items-card">
            <h3 style={{ marginBottom: '1rem' }}>Order Items ({cart.length})</h3>

            {cart.map((item) => {
              const subtotal = parseFloat(item.product.selling_price) * item.quantity;
              const maxStock = item.product.inventory?.quantity ?? 99;

              return (
                <div key={item.product.id} className="cart-item-row">
                  <div>
                    <h4 style={{ fontSize: '1.05rem', fontWeight: 600 }}>{item.product.name}</h4>
                    <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
                      SKU: {item.product.sku} | Unit Price: ${parseFloat(item.product.selling_price).toFixed(2)}
                    </div>
                  </div>

                  <div style={{ display: 'flex', alignItems: 'center', gap: '1.5rem' }}>
                    <div className="qty-control">
                      <button
                        className="qty-btn"
                        onClick={() => onUpdateQuantity(item.product.id, item.quantity - 1)}
                      >
                        -
                      </button>
                      <span style={{ fontWeight: 600, minWidth: '24px', textAlign: 'center' }}>
                        {item.quantity}
                      </span>
                      <button
                        className="qty-btn"
                        disabled={item.quantity >= maxStock}
                        onClick={() => onUpdateQuantity(item.product.id, item.quantity + 1)}
                      >
                        +
                      </button>
                    </div>

                    <div style={{ fontWeight: 700, minWidth: '80px', textAlign: 'right' }}>
                      ${subtotal.toFixed(2)}
                    </div>

                    <button
                      className="btn btn-sm btn-outline"
                      style={{ color: 'var(--danger)', borderColor: 'var(--danger)' }}
                      onClick={() => onRemoveItem(item.product.id)}
                    >
                      Remove
                    </button>
                  </div>
                </div>
              );
            })}
          </div>

          {/* Checkout Summary Card */}
          <div className="cart-summary-card">
            <h3 style={{ marginBottom: '1.25rem' }}>Order Summary</h3>

            <div className="form-group">
              <label>Select Customer</label>
              <select
                className="select-input"
                style={{ width: '100%' }}
                value={selectedCustomerId}
                onChange={(e) => setSelectedCustomerId(e.target.value)}
              >
                {customers.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name} ({c.email})
                  </option>
                ))}
              </select>
            </div>

            <div className="summary-row">
              <span>Items Subtotal:</span>
              <span>${calculateTotal().toFixed(2)}</span>
            </div>
            <div className="summary-row">
              <span>Shipping & Tax:</span>
              <span>$0.00 (Free)</span>
            </div>
            <div className="summary-row summary-total">
              <span>Total Amount:</span>
              <span>${calculateTotal().toFixed(2)}</span>
            </div>

            {/* Simulated Failure Checkbox for DBMS ACID demonstration */}
            <div style={{
              background: '#f8fafc',
              border: '1px dashed #cbd5e1',
              padding: '0.75rem',
              borderRadius: 'var(--radius)',
              margin: '1.25rem 0'
            }}>
              <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer', fontSize: '0.875rem' }}>
                <input
                  type="checkbox"
                  checked={simulateFailure}
                  onChange={(e) => setSimulateFailure(e.target.checked)}
                />
                <strong>Simulate Payment Gateway Failure</strong>
              </label>
              <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.25rem' }}>
                Tests DBMS Atomicity: Verifies order rollback and inventory restitution if payment fails.
              </p>
            </div>

            <button
              className="btn btn-success"
              style={{ width: '100%', padding: '0.8rem' }}
              disabled={loading || cart.length === 0}
              onClick={handlePlaceOrder}
            >
              {loading ? 'Executing ACID Transaction...' : `Place Order ($${calculateTotal().toFixed(2)})`}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
