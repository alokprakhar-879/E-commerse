import React, { useState, useEffect } from 'react';
import { api } from '../api';

export default function InventoryPage() {
  const [products, setProducts] = useState([]);
  const [categories, setCategories] = useState([]);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState(null);

  // Modal State for Add / Edit
  const [showModal, setShowModal] = useState(false);
  const [editingProduct, setEditingProduct] = useState(null);
  const [formData, setFormData] = useState({
    name: '',
    category_id: '',
    sku: '',
    cost_price: '',
    selling_price: '',
    description: '',
    initial_quantity: 10,
    reorder_level: 5,
  });

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setLoading(true);
    try {
      const [prods, cats] = await Promise.all([
        api.getProducts(),
        api.getCategories(),
      ]);
      setProducts(prods);
      setCategories(cats);
    } catch (err) {
      console.error('Failed to load inventory data', err);
    } finally {
      setLoading(false);
    }
  };

  const handleOpenAddModal = () => {
    setEditingProduct(null);
    setFormData({
      name: '',
      category_id: categories[0]?.id || '',
      sku: '',
      cost_price: '',
      selling_price: '',
      description: '',
      initial_quantity: 10,
      reorder_level: 5,
    });
    setShowModal(true);
  };

  const handleOpenEditModal = (p) => {
    setEditingProduct(p);
    setFormData({
      name: p.name,
      category_id: p.category_id,
      sku: p.sku,
      cost_price: p.cost_price,
      selling_price: p.selling_price,
      description: p.description || '',
      initial_quantity: p.inventory?.quantity ?? 0,
      reorder_level: p.inventory?.reorder_level ?? 5,
    });
    setShowModal(true);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setMessage(null);

    try {
      if (editingProduct) {
        // Update product & inventory
        await api.updateProduct(editingProduct.id, {
          name: formData.name,
          category_id: parseInt(formData.category_id),
          sku: formData.sku,
          cost_price: parseFloat(formData.cost_price),
          selling_price: parseFloat(formData.selling_price),
          description: formData.description,
          quantity: parseInt(formData.initial_quantity),
          reorder_level: parseInt(formData.reorder_level),
        });
        setMessage({ type: 'success', text: `Product "${formData.name}" updated successfully.` });
      } else {
        // Create product (atomic 1-1 inventory creation)
        await api.createProduct({
          name: formData.name,
          category_id: parseInt(formData.category_id),
          sku: formData.sku,
          cost_price: parseFloat(formData.cost_price),
          selling_price: parseFloat(formData.selling_price),
          description: formData.description,
          initial_quantity: parseInt(formData.initial_quantity),
          reorder_level: parseInt(formData.reorder_level),
        });
        setMessage({ type: 'success', text: `Product "${formData.name}" and inventory created in single ACID transaction.` });
      }
      setShowModal(false);
      loadData();
    } catch (err) {
      setMessage({ type: 'danger', text: err.message || 'Operation failed' });
    }
  };

  const handleQuickStockUpdate = async (product, newQty) => {
    if (newQty < 0) return;
    try {
      await api.updateInventory(product.id, { quantity: newQty });
      setProducts((prev) =>
        prev.map((p) =>
          p.id === product.id
            ? { ...p, inventory: { ...p.inventory, quantity: newQty } }
            : p
        )
      );
    } catch (err) {
      setMessage({ type: 'danger', text: err.message || 'Failed to update stock' });
    }
  };

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">Inventory & Stock Control</h1>
          <p className="page-subtitle">
            Manage stock levels, configure reorder thresholds, and maintain 3NF product records.
            Low-stock rows are highlighted in red.
          </p>
        </div>
        <button className="btn btn-primary" onClick={handleOpenAddModal}>
          + Add New Product
        </button>
      </div>

      {message && (
        <div className={`alert-banner alert-${message.type}`}>
          <span>{message.text}</span>
          <button className="btn btn-sm btn-outline" onClick={() => setMessage(null)}>✕</button>
        </div>
      )}

      {loading ? (
        <p>Loading inventory records...</p>
      ) : (
        <div className="table-wrapper">
          <table className="data-table">
            <thead>
              <tr>
                <th>Product & SKU</th>
                <th>Category</th>
                <th>Cost Price</th>
                <th>Selling Price</th>
                <th>Stock Quantity</th>
                <th>Reorder Level</th>
                <th>Status</th>
                <th>Quick Actions</th>
              </tr>
            </thead>
            <tbody>
              {products.map((p) => {
                const qty = p.inventory?.quantity ?? 0;
                const reorder = p.inventory?.reorder_level ?? 5;
                const isLowStock = qty <= reorder;

                return (
                  <tr key={p.id} className={isLowStock ? 'row-low-stock' : ''}>
                    <td>
                      <strong>{p.name}</strong>
                      <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                        SKU: {p.sku}
                      </div>
                    </td>
                    <td>{p.category_name}</td>
                    <td>${parseFloat(p.cost_price).toFixed(2)}</td>
                    <td>${parseFloat(p.selling_price).toFixed(2)}</td>
                    <td>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                        <button
                          className="qty-btn"
                          disabled={qty <= 0}
                          onClick={() => handleQuickStockUpdate(p, qty - 1)}
                        >
                          -
                        </button>
                        <strong style={{ minWidth: '28px', textAlign: 'center' }}>{qty}</strong>
                        <button
                          className="qty-btn"
                          onClick={() => handleQuickStockUpdate(p, qty + 1)}
                        >
                          +
                        </button>
                      </div>
                    </td>
                    <td>{reorder}</td>
                    <td>
                      <span className={`stock-pill ${isLowStock ? 'stock-low' : 'stock-healthy'}`}>
                        {isLowStock ? '⚠️ Low Stock' : '✓ Normal'}
                      </span>
                    </td>
                    <td>
                      <button
                        className="btn btn-sm btn-outline"
                        onClick={() => handleOpenEditModal(p)}
                      >
                        Edit Details
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {/* Add / Edit Product Modal */}
      {showModal && (
        <div className="modal-backdrop" onClick={() => setShowModal(false)}>
          <div className="modal-card" onClick={(e) => e.stopPropagation()}>
            <h3 style={{ marginBottom: '1.25rem' }}>
              {editingProduct ? 'Edit Product & Inventory' : 'Add New Product (Atomic Transaction)'}
            </h3>

            <form onSubmit={handleSubmit}>
              <div className="form-group">
                <label>Product Name *</label>
                <input
                  type="text"
                  required
                  className="form-control"
                  style={{ width: '100%' }}
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                />
              </div>

              <div className="form-row">
                <div className="form-group">
                  <label>SKU (Unique) *</label>
                  <input
                    type="text"
                    required
                    className="form-control"
                    style={{ width: '100%' }}
                    value={formData.sku}
                    onChange={(e) => setFormData({ ...formData, sku: e.target.value })}
                  />
                </div>
                <div className="form-group">
                  <label>Category *</label>
                  <select
                    className="select-input"
                    style={{ width: '100%' }}
                    value={formData.category_id}
                    onChange={(e) => setFormData({ ...formData, category_id: e.target.value })}
                  >
                    {categories.map((c) => (
                      <option key={c.id} value={c.id}>{c.name}</option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="form-row">
                <div className="form-group">
                  <label>Cost Price ($) *</label>
                  <input
                    type="number"
                    step="0.01"
                    min="0.01"
                    required
                    className="form-control"
                    style={{ width: '100%' }}
                    value={formData.cost_price}
                    onChange={(e) => setFormData({ ...formData, cost_price: e.target.value })}
                  />
                </div>
                <div className="form-group">
                  <label>Selling Price ($) *</label>
                  <input
                    type="number"
                    step="0.01"
                    min="0.01"
                    required
                    className="form-control"
                    style={{ width: '100%' }}
                    value={formData.selling_price}
                    onChange={(e) => setFormData({ ...formData, selling_price: e.target.value })}
                  />
                </div>
              </div>

              <div className="form-row">
                <div className="form-group">
                  <label>Quantity *</label>
                  <input
                    type="number"
                    min="0"
                    required
                    className="form-control"
                    style={{ width: '100%' }}
                    value={formData.initial_quantity}
                    onChange={(e) => setFormData({ ...formData, initial_quantity: e.target.value })}
                  />
                </div>
                <div className="form-group">
                  <label>Reorder Threshold *</label>
                  <input
                    type="number"
                    min="0"
                    required
                    className="form-control"
                    style={{ width: '100%' }}
                    value={formData.reorder_level}
                    onChange={(e) => setFormData({ ...formData, reorder_level: e.target.value })}
                  />
                </div>
              </div>

              <div className="form-group">
                <label>Description</label>
                <textarea
                  className="form-control"
                  style={{ width: '100%', minHeight: '60px' }}
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                />
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.75rem', marginTop: '1.5rem' }}>
                <button type="button" className="btn btn-outline" onClick={() => setShowModal(false)}>
                  Cancel
                </button>
                <button type="submit" className="btn btn-primary">
                  {editingProduct ? 'Save Changes' : 'Create Product & Stock'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
