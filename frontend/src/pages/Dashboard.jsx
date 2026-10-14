import { useState, useEffect, useCallback } from "react";
import { Link } from "react-router-dom";
import { Package, Users, ShoppingCart, AlertTriangle, ArrowUpRight, RefreshCw, Bot, ArrowRight, TrendingUp } from "lucide-react";
import { getProducts, getDealers, getOrders, getReorderSuggestions } from "../services/api";
import { StatusBadge, StockBadge } from "../components/Badge";
import { CardSkeleton, TableSkeleton } from "../components/LoadingSkeleton";
import { EmptyState } from "../components/EmptyState";

export function Dashboard() {
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState({ products: 0, dealers: 0, orders: 0, reorders: 0 });
  const [reorders, setReorders] = useState([]);
  const [orders, setOrders] = useState([]);
  const [error, setError] = useState(null);
  const [updatedAt, setUpdatedAt] = useState(null);
  const load = useCallback(async () => {
    setLoading(true); setError(null);
    try {
      const [products, dealers, orderData, reorderData] = await Promise.all([
        getProducts({ page_size: 1 }), getDealers({ page_size: 1 }), getOrders({ page_size: 5 }), getReorderSuggestions(),
      ]);
      const urgent = (reorderData.results || []).filter(item => item.reorder_qty > 0);
      setStats({ products: products.count || 0, dealers: dealers.count || 0, orders: orderData.count || 0, reorders: urgent.length });
      setReorders(urgent.slice(0, 5)); setOrders(orderData.results || []); setUpdatedAt(new Date());
    } catch (err) { setError(err.message || "Could not load workspace overview."); }
    finally { setLoading(false); }
  }, []);

  const metrics = [
    { label: "Total products", value: stats.products, caption: "SKUs in your catalogue", icon: Package, path: "/products" },
    { label: "Dealer network", value: stats.dealers, caption: "Registered distribution partners", icon: Users, path: "/dealers" },
    { label: "Total orders", value: stats.orders, caption: "Across all order statuses", icon: ShoppingCart, path: "/orders" },
    { label: "Reorder alerts", value: stats.reorders, caption: "Forecast SKUs requiring replenishment", icon: AlertTriangle, path: "/forecasting", warning: true },
  ];
  useEffect(() => {
    // Loading state tracks this external API request.
    // oxlint-disable-next-line react/set-state-in-effect
    load();
  }, [load]);

  return <div className="space-y-6">
    <div className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-4">
      <div><p className="text-xs text-secondary mb-2">WORKSPACE OVERVIEW</p><h1>Everything in view.</h1><p className="text-sm text-secondary mt-2">Your catalogue, dealer network, and orders. Connected in one workspace.</p></div>
      <button className="btn-secondary text-xs self-start" onClick={load} disabled={loading}><RefreshCw size={14} /><span>Refresh overview</span></button>
    </div>
    {error ? <div className="notice-error p-5 rounded-lg" role="alert"><strong>Overview unavailable</strong><p className="text-sm mt-1 mb-3">{error}</p><button className="btn-secondary text-xs" onClick={load}>Try again</button></div> : loading ? <><CardSkeleton count={4} /><div className="panel"><TableSkeleton rows={5} cols={4} /></div></> : <>
      <div className="kpi-grid grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
        {metrics.map(metric => <Link key={metric.label} to={metric.path} className="panel kpi-card p-5">
          <div className="flex items-center justify-between gap-2 mb-5"><span className="text-xs font-medium text-secondary">{metric.label}</span><metric.icon size={17} className={metric.warning ? "text-warning-ink" : "text-secondary"} /></div>
          <div className={`kpi-value ${metric.warning ? "text-warning-ink" : "text-foreground"}`}>{metric.value.toLocaleString("en-IN")}</div>
          <div className="text-[11px] text-secondary mt-2">{metric.caption}</div>
        </Link>)}
      </div>
      <div className="flex items-center justify-between text-[11px] text-secondary"><span>Live workspace data</span><span>Updated {updatedAt?.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}</span></div>
      <div className="grid grid-cols-1 xl:grid-cols-2 gap-5">
        <section className="panel overflow-hidden">
          <div className="p-5 border-b border-line flex items-center justify-between gap-3"><div><h2 className="font-semibold text-base">Recent orders</h2><p className="text-xs text-secondary mt-1">The latest activity across your dealer network</p></div><Link to="/orders" className="text-xs font-medium text-primary inline-flex items-center gap-1 whitespace-nowrap">View orders<ArrowUpRight size={14} /></Link></div>
          {orders.length === 0 ? <EmptyState title="No orders yet" description="Create a draft order to get started." action={<Link className="btn-secondary text-xs" to="/orders">Manage orders</Link>} /> : <div className="overflow-x-auto"><table className="text-left"><thead><tr><th className="px-5 py-3">Order</th><th className="px-4 py-3">Status</th><th className="px-4 py-3">Created</th><th className="px-5 py-3 text-right">Order value</th></tr></thead><tbody>{orders.map(order => <tr key={order.order_number}><td className="px-5 py-4 font-medium whitespace-nowrap"><Link to={`/orders?order=${encodeURIComponent(order.order_number)}`} className="hover:text-primary">{order.order_number}</Link></td><td className="px-4 py-4"><StatusBadge status={order.status} /></td><td className="px-4 py-4 text-secondary whitespace-nowrap">{new Date(order.created_at).toLocaleDateString("en-IN", { day: "numeric", month: "short" })}</td><td className="px-5 py-4 text-right font-medium whitespace-nowrap">₹{Number(order.grand_total || 0).toLocaleString("en-IN", { minimumFractionDigits: 2 })}</td></tr>)}</tbody></table></div>}
        </section>
        <section className="panel overflow-hidden">
          <div className="p-5 border-b border-line flex items-center justify-between gap-3"><div><h2 className="font-semibold text-base">Inventory attention</h2><p className="text-xs text-secondary mt-1">Replenishment recommendations from demand forecasts</p></div><Link to="/forecasting" className="text-xs font-medium text-primary inline-flex items-center gap-1 whitespace-nowrap">View all<ArrowUpRight size={14} /></Link></div>
          {reorders.length === 0 ? <EmptyState icon={TrendingUp} title="No reorder alerts" description="No forecast SKUs currently require replenishment." /> : <div className="overflow-x-auto"><table className="text-left"><thead><tr><th className="px-5 py-3">SKU</th><th className="px-4 py-3">Available stock</th><th className="px-4 py-3">Lead demand</th><th className="px-5 py-3 text-right">Reorder</th></tr></thead><tbody>{reorders.map(item => <tr key={item.sku}><td className="px-5 py-4 font-mono font-medium"><Link to={`/products?search=${encodeURIComponent(item.sku)}`} className="hover:text-primary">{item.sku}</Link></td><td className="px-4 py-4"><StockBadge stock={item.current_stock} /></td><td className="px-4 py-4 text-secondary">{item.lead_time_demand}</td><td className="px-5 py-4 text-right font-semibold text-warning-ink">+{item.reorder_qty}</td></tr>)}</tbody></table></div>}
        </section>
      </div>
    </>}
    <div className="insight-banner"><div className="flex gap-4 items-start"><span className="p-2 bg-surface border border-primary-line rounded-lg text-primary"><Bot size={20} /></span><div><h2 className="font-semibold text-sm">A faster way to find the right part.</h2><p className="text-xs text-secondary mt-1">Search by vehicle fitment, check live stock, and prepare dealer orders with the assistant.</p></div></div><Link to="/assistant" className="btn-primary text-xs">Open assistant<ArrowRight size={14} /></Link></div>
  </div>;
}
