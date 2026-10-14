import { useState, useEffect, useRef } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { LayoutDashboard, Package, Users, ShoppingCart, Bot, TrendingUp, Menu, X, Wrench, CheckCircle2, AlertCircle, RefreshCw, PanelLeftClose, PanelLeftOpen, Search, Sun, Moon, Monitor, ChevronRight } from "lucide-react";
import { getHealth, triggerSupplierSync } from "../services/api";
import { useTheme } from "./theme-context";
import { Modal } from "./Modal";
const NAV_ITEMS = [
  { name: "Overview", path: "/", icon: LayoutDashboard },
  { name: "Products & inventory", path: "/products", icon: Package },
  { name: "Dealers", path: "/dealers", icon: Users },
  { name: "Orders", path: "/orders", icon: ShoppingCart },
  { name: "AI assistant", path: "/assistant", icon: Bot },
  { name: "Demand forecasting", path: "/forecasting", icon: TrendingUp },
];
export function Layout({ children }) {
  const location = useLocation(), navigate = useNavigate();
  const { theme, setTheme } = useTheme();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [collapsed, setCollapsed] = useState(() => { try { return localStorage.getItem("vikmo-sidebar") === "collapsed"; } catch { return false; } });
  const [healthy, setHealthy] = useState(null);
  const [syncing, setSyncing] = useState(false);
  const [syncResult, setSyncResult] = useState(null);
  const [search, setSearch] = useState("");
  const syncTimer = useRef(null);
  const current = NAV_ITEMS.find(item => item.path === location.pathname) || NAV_ITEMS[0];
  useEffect(() => {
    let active = true;
    const check = async () => { try { const result = await getHealth(); if (active) setHealthy(result.status === "ok"); } catch { if (active) setHealthy(false); } };
    check(); const timer = setInterval(check, 30000);
    return () => { active = false; clearInterval(timer); clearTimeout(syncTimer.current); };
  }, []);
  useEffect(() => { document.title = `${current.name} · VIKMO Dealer Desk`; }, [current.name]);
  const toggleSidebar = () => {
    setCollapsed(!collapsed);
    try { localStorage.setItem("vikmo-sidebar", !collapsed ? "collapsed" : "expanded"); } catch { /* Optional persistence. */ }
  };
  const sync = async () => {
    setSyncing(true); setSyncResult(null); clearTimeout(syncTimer.current);
    try { const result = await triggerSupplierSync(); setSyncResult({ text: `Supplier feed synced. ${result.created} added, ${result.updated} updated.`, success: true }); }
    catch (error) { setSyncResult({ text: error.message, success: false }); }
    finally { setSyncing(false); syncTimer.current = setTimeout(() => setSyncResult(null), 8000); }
  };
  const navigation = <>
    <Link to="/" className="brand" onClick={() => setMobileOpen(false)} aria-label="VIKMO Dealer Desk home"><span className="brand-icon"><Wrench size={20} /></span><span className="sidebar-label"><strong>VIKMO</strong><small>Dealer Desk</small></span></Link>
    <nav className="sidebar-nav" aria-label="Main navigation">{NAV_ITEMS.map((item, index) => <div key={item.path}>
      {(index === 0 || index === 4) && <div className="nav-section sidebar-label">{index === 0 ? "Workspace" : "Intelligence"}</div>}
      <Link to={item.path} title={item.name} aria-label={item.name} aria-current={location.pathname === item.path ? "page" : undefined} className={`nav-item ${location.pathname === item.path ? "active" : ""}`} onClick={() => setMobileOpen(false)}><item.icon size={18} /><span className="sidebar-label">{item.name}</span></Link>
    </div>)}</nav>
    <div className="sidebar-footer">
      <div className="api-status" title={healthy === null ? "Checking API connection" : healthy ? "API connected" : "API unavailable"}>{healthy === false ? <AlertCircle size={16} className="text-danger" /> : <CheckCircle2 size={16} className={healthy ? "text-success" : "text-muted"} />}<span className="sidebar-label">{healthy === null ? "Connecting…" : healthy ? "API connected" : "API unavailable"}</span></div>
      <button className="sync-button" onClick={sync} disabled={syncing} title="Sync supplier feed" aria-label="Sync supplier feed"><RefreshCw size={16} className={syncing ? "animate-spin" : ""} /><span className="sidebar-label">{syncing ? "Syncing supplier…" : "Sync supplier feed"}</span></button>
      <div className="workspace-identity sidebar-label"><span className="workspace-avatar">V</span><div><strong>Distribution workspace</strong><small>Automotive operations</small></div></div>
    </div>
  </>;
  return <div className={`app-shell ${collapsed ? "sidebar-collapsed" : ""}`}>
    <a className="skip-link" href="#main-content">Skip to content</a>
    <aside className="desktop-sidebar">{navigation}<button className="collapse-button" onClick={toggleSidebar} aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"} title={collapsed ? "Expand sidebar" : "Collapse sidebar"}>{collapsed ? <PanelLeftOpen size={17} /> : <PanelLeftClose size={17} />}<span className="sidebar-label">Collapse sidebar</span></button></aside>
    {mobileOpen && <Modal label="Navigation" onClose={() => setMobileOpen(false)}>{closeModal => <aside className="mobile-sidebar"><button className="icon-button drawer-close" onClick={closeModal} aria-label="Close navigation"><X size={20} /></button>{navigation}</aside>}</Modal>}
    <div className="workspace-main">
      <header className="topbar"><div className="header-context"><button className="icon-button mobile-toggle" onClick={() => setMobileOpen(true)} aria-label="Open navigation"><Menu size={20} /></button><span className="breadcrumb-root">Workspace</span><ChevronRight size={14} className="breadcrumb-root" /><span>{current.name}</span></div><div className="header-actions">
        <form className="global-search" onSubmit={event => { event.preventDefault(); if (search.trim()) navigate(`/products?search=${encodeURIComponent(search.trim())}`); }}><Search size={16} /><input aria-label="Search product catalogue" placeholder="Search products…" value={search} onChange={event => setSearch(event.target.value)} /><button type="submit" title="Search catalogue" aria-label="Search catalogue"><ChevronRight size={15} /></button></form>
        <div className="theme-control"><span aria-hidden="true">{theme === "dark" ? <Moon size={16} /> : theme === "light" ? <Sun size={16} /> : <Monitor size={16} />}</span><select aria-label="Color theme" value={theme} onChange={event => setTheme(event.target.value)}><option value="light">Light</option><option value="dark">Dark</option><option value="system">System</option></select></div>
      </div></header>
      {syncResult && <div role={syncResult.success ? "status" : "alert"} className={`sync-notice ${syncResult.success ? "notice-success" : "notice-error"}`}>{syncResult.text}<button className="icon-button" onClick={() => setSyncResult(null)} aria-label="Dismiss notification"><X size={16} /></button></div>}
      <main id="main-content" tabIndex={-1} className="page-content"><div key={location.pathname} className="page-transition">{children}</div></main>
    </div>
  </div>;
}
