import React, { useState, useEffect } from 'react';
import { api } from '../api';

export default function ProductsPage({ onAddToCart, cartItems }) {
  const [products, setProducts] = useState([]);
  const [categories, setCategories] = useState([]);
  const [selectedCategory, setSelectedCategory] = useState('');
  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState(null);

  useEffect(() => {
    loadCategories();
  }, []);

  useEffect(() => {
    loadProducts();
  }, [selectedCategory, search]);

  const loadCategories = async () => {
    try {
      const data = await api.getCategories();
      setCategories(data);
    } catch (err) {
      console.error('Failed to load categories', err);
    }
  };

  const loadProducts = async () => {
    setLoading(true);
    try {
      const data = await api.getProducts(selectedCategory || null, search || null);
      setProducts(data);
    } catch (err) {
      console.error('Failed to load products', err);
    } finally {
      setLoading(false);
    }
  };

  const handleAddToCart = (product) => {
    const availableStock = product.inventory?.quantity ?? 0;
    const currentInCart = cartItems.find((i) => i.product.id === product.id)?.quantity || 0;

    if (currentInCart + 1 > availableStock) {
      setMessage({ type: 'danger', text: `Cannot add more: Only ${availableStock} units in stock for "${product.name}".` });
      setTimeout(() => setMessage(null), 4000);
      return;
    }

    onAddToCart(product);
    setMessage({ type: 'success', text: `Added "${product.name}" to cart!` });
    setTimeout(() => setMessage(null), 3000);
  };

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">Product Catalog</h1>
          <p className="page-subtitle">Browse products, check live inventory, and add items to your cart</p>
        </div>
      </div>

      {message && (
        <div className={`alert-banner alert-${message.type}`}>
          <span>{message.text}</span>
          <button className="btn btn-sm btn-outline" onClick={() => setMessage(null)}>✕</button>
        </div>
      )}

      <div className="filters-bar">
        <input
          type="text"
          className="search-input"
          placeholder="Search by product name or SKU..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        <select
          className="select-input"
          value={selectedCategory}
          onChange={(e) => setSelectedCategory(e.target.value)}
        >
          <option value="">All Categories ({categories.length})</option>
          {categories.map((c) => (
            <option key={c.id} value={c.id}>{c.name}</option>
          ))}
        </select>
        {(selectedCategory || search) && (
          <button
            className="btn btn-outline"
            onClick={() => { setSelectedCategory(''); setSearch(''); }}
          >
            Clear Filters
          </button>
        )}
      </div>

      {loading ? (
        <p>Loading products from database...</p>
      ) : products.length === 0 ? (
        <div className="alert-banner alert-info">
          No products found matching your search.
        </div>
      ) : (
        <div className="products-grid">
          {products.map((p) => {
            const stock = p.inventory?.quantity ?? 0;
            const reorder = p.inventory?.reorder_level ?? 5;
            const isLowStock = stock <= reorder;

            return (
              <div key={p.id} className="product-card">
                <div>
                  <div className="product-category-tag">{p.category_name || 'General'}</div>
                  <h3 className="product-name">{p.name}</h3>
                  <div className="product-sku">SKU: {p.sku}</div>
                  <p className="product-desc">{p.description || 'No description provided.'}</p>
                </div>

                <div>
                  <div className="product-footer">
                    <div>
                      <div className="product-price">${parseFloat(p.selling_price).toFixed(2)}</div>
                      <span className={`stock-pill ${isLowStock ? 'stock-low' : 'stock-healthy'}`}>
                        {stock > 0 ? `${stock} in stock` : 'Out of stock'}
                      </span>
                    </div>

                    <button
                      className="btn btn-primary btn-sm"
                      disabled={stock <= 0}
                      onClick={() => handleAddToCart(p)}
                    >
                      {stock > 0 ? '+ Add to Cart' : 'Unavailable'}
                    </button>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
