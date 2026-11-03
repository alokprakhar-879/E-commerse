import React, { useState, useEffect, useRef } from 'react';
import { Chart, registerables } from 'chart.js';
import { api } from '../api';

Chart.register(...registerables);

export default function DashboardPage({ onNavigateToInventory }) {
  const [salesData, setSalesData] = useState([]);
  const [profitData, setProfitData] = useState({ by_product: [], by_category: [] });
  const [topProducts, setTopProducts] = useState([]);
  const [lowStockItems, setLowStockItems] = useState([]);
  const [loading, setLoading] = useState(true);

  const salesCanvasRef = useRef(null);
  const profitCanvasRef = useRef(null);
  const topProdCanvasRef = useRef(null);

  const salesChartInstance = useRef(null);
  const profitChartInstance = useRef(null);
  const topProdChartInstance = useRef(null);

  useEffect(() => {
    loadDashboardData();
  }, []);

  const loadDashboardData = async () => {
    setLoading(true);
    try {
      const [sales, profit, top, lowStock] = await Promise.all([
        api.getSalesReport(),
        api.getProfitReport(),
        api.getTopProductsReport(5),
        api.getLowStock(),
      ]);
      setSalesData(sales);
      setProfitData(profit);
      setTopProducts(top);
      setLowStockItems(lowStock);
    } catch (err) {
      console.error('Failed to load dashboard metrics', err);
    } finally {
      setLoading(false);
    }
  };

  // Render Charts once data is loaded
  useEffect(() => {
    if (loading) return;

    // 1. Sales Over Time (Line Chart)
    if (salesCanvasRef.current) {
      if (salesChartInstance.current) salesChartInstance.current.destroy();

      const labels = salesData.map((d) => d.date);
      const values = salesData.map((d) => parseFloat(d.total_sales));

      salesChartInstance.current = new Chart(salesCanvasRef.current, {
        type: 'line',
        data: {
          labels: labels.length ? labels : ['No Data'],
          datasets: [
            {
              label: 'Daily Sales ($)',
              data: values.length ? values : [0],
              borderColor: '#2563eb',
              backgroundColor: 'rgba(37, 99, 235, 0.1)',
              borderWidth: 2,
              fill: true,
              tension: 0.3,
            },
          ],
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: { display: true, position: 'top' },
            tooltip: {
              callbacks: {
                label: (ctx) => `Sales: $${ctx.parsed.y.toFixed(2)}`,
              },
            },
          },
          scales: {
            y: {
              beginAtZero: true,
              ticks: { callback: (val) => `$${val}` },
            },
          },
        },
      });
    }

    // 2. Profit by Category (Bar Chart)
    if (profitCanvasRef.current) {
      if (profitChartInstance.current) profitChartInstance.current.destroy();

      const catLabels = profitData.by_category.map((c) => c.category_name);
      const catProfits = profitData.by_category.map((c) => parseFloat(c.profit));
      const catRevenues = profitData.by_category.map((c) => parseFloat(c.revenue));

      profitChartInstance.current = new Chart(profitCanvasRef.current, {
        type: 'bar',
        data: {
          labels: catLabels.length ? catLabels : ['No Data'],
          datasets: [
            {
              label: 'Gross Profit ($)',
              data: catProfits.length ? catProfits : [0],
              backgroundColor: '#16a34a',
            },
            {
              label: 'Revenue ($)',
              data: catRevenues.length ? catRevenues : [0],
              backgroundColor: '#93c5fd',
            },
          ],
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: { position: 'top' },
          },
          scales: {
            y: {
              beginAtZero: true,
              ticks: { callback: (val) => `$${val}` },
            },
          },
        },
      });
    }

    // 3. Top 5 Products by Revenue (Bar Chart)
    if (topProdCanvasRef.current) {
      if (topProdChartInstance.current) topProdChartInstance.current.destroy();

      const prodLabels = topProducts.map((p) => p.name);
      const revenues = topProducts.map((p) => parseFloat(p.total_revenue));

      topProdChartInstance.current = new Chart(topProdCanvasRef.current, {
        type: 'bar',
        data: {
          labels: prodLabels.length ? prodLabels : ['No Data'],
          datasets: [
            {
              label: 'Revenue ($)',
              data: revenues.length ? revenues : [0],
              backgroundColor: '#8b5cf6',
            },
          ],
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          indexAxis: 'y', // horizontal bar
          plugins: {
            legend: { display: false },
            tooltip: {
              callbacks: {
                label: (ctx) => `Total Revenue: $${ctx.parsed.x.toFixed(2)}`,
              },
            },
          },
          scales: {
            x: {
              beginAtZero: true,
              ticks: { callback: (val) => `$${val}` },
            },
          },
        },
      });
    }

    return () => {
      if (salesChartInstance.current) salesChartInstance.current.destroy();
      if (profitChartInstance.current) profitChartInstance.current.destroy();
      if (topProdChartInstance.current) topProdChartInstance.current.destroy();
    };
  }, [salesData, profitData, topProducts, loading]);

  const totalRevenue = salesData.reduce((sum, d) => sum + parseFloat(d.total_sales), 0);
  const totalOrders = salesData.reduce((sum, d) => sum + d.order_count, 0);

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">Executive Analytics Dashboard</h1>
          <p className="page-subtitle">Real-time DBMS reporting, SQL aggregates, and inventory health</p>
        </div>
        <button className="btn btn-outline" onClick={loadDashboardData}>
          ↻ Refresh Analytics
        </button>
      </div>

      {/* Low-Stock Alert Banner */}
      {lowStockItems.length > 0 && (
        <div className="alert-banner alert-danger">
          <div>
            <strong>⚠️ Low-Stock Alert:</strong> {lowStockItems.length} product{lowStockItems.length > 1 ? 's have' : ' has'} fallen below the reorder threshold!
            <span style={{ marginLeft: '0.75rem', fontSize: '0.875rem' }}>
              ({lowStockItems.map((i) => `${i.name} [qty: ${i.quantity}]`).join(', ')})
            </span>
          </div>
          <button className="btn btn-sm btn-danger" onClick={onNavigateToInventory}>
            Manage Stock →
          </button>
        </div>
      )}

      {/* Summary KPI Cards */}
      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-label">Total Confirmed Revenue</div>
          <div className="stat-value" style={{ color: 'var(--success)' }}>
            ${totalRevenue.toFixed(2)}
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Paid Orders Completed</div>
          <div className="stat-value" style={{ color: 'var(--primary)' }}>
            {totalOrders}
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Low Stock Alerts</div>
          <div className="stat-value" style={{ color: lowStockItems.length > 0 ? 'var(--danger)' : 'var(--success)' }}>
            {lowStockItems.length}
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Top Selling Categories</div>
          <div className="stat-value" style={{ color: '#8b5cf6' }}>
            {profitData.by_category.length}
          </div>
        </div>
      </div>

      {/* Chart.js Visualizations */}
      <div className="charts-grid">
        {/* Sales Over Time (Line) */}
        <div className="chart-card chart-card-full">
          <h3 className="chart-title">Sales Over Time (PAID Orders Trend)</h3>
          <div className="chart-container">
            <canvas ref={salesCanvasRef}></canvas>
          </div>
        </div>

        {/* Profit by Category (Bar) */}
        <div className="chart-card">
          <h3 className="chart-title">Profit & Revenue by Category</h3>
          <div className="chart-container">
            <canvas ref={profitCanvasRef}></canvas>
          </div>
        </div>

        {/* Top 5 Products by Revenue (Bar) */}
        <div className="chart-card">
          <h3 className="chart-title">Top 5 Products by Revenue</h3>
          <div className="chart-container">
            <canvas ref={topProdCanvasRef}></canvas>
          </div>
        </div>
      </div>
    </div>
  );
}
