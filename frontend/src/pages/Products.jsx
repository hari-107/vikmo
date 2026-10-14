import { Modal } from "../components/Modal";
import { useSearchParams } from "react-router-dom";
import React, { useState, useEffect, useCallback } from "react";
import {
  Search,
  Plus,
  Edit3,
  X,
  AlertCircle,
} from "lucide-react";
import {
  getProducts,
  updateInventory,
  createProduct,
  patchProduct,
} from "../services/api";
import { StockBadge } from "../components/Badge";
import { TableSkeleton } from "../components/LoadingSkeleton";
import { EmptyState } from "../components/EmptyState";

const CATEGORIES = [
  "All Categories",
  "Accessories",
  "Batteries & Electricals",
  "Body & Styling",
  "Brakes",
  "Cables & Controls",
  "Car Care",
  "Chain & Sprockets",
  "Controls & Grips",
  "Drivetrain",
  "Engine & Oils",
  "Filters",
  "Grips & Levers",
  "Lighting & Electrical",
  "Lighting & Indicators",
  "Rider Gear",
  "Tyres & Tubes",
  "Universal Accessories",
];

const VEHICLES = [
  "All Vehicles",
  "Bajaj Dominar 400",
  "Bajaj Pulsar 150",
  "Bajaj Pulsar NS200",
  "Hero Splendor Plus",
  "Hero Xtreme 160R",
  "Honda Activa 6G",
  "Honda CB Shine",
  "Honda Hornet 2.0",
  "Honda Shine 125",
  "Hyundai Creta",
  "Hyundai i20",
  "KTM Duke 200",
  "KTM Duke 390",
  "Mahindra Thar",
  "Maruti Baleno",
  "Maruti Swift",
  "Royal Enfield Classic 350",
  "Royal Enfield Himalayan 450",
  "Royal Enfield Hunter 350",
  "Suzuki Gixxer SF",
  "TVS Apache RTR 160",
  "TVS Apache RTR 200",
  "Tata Nexon",
  "Universal",
  "Yamaha FZ-S",
  "Yamaha MT-15",
  "Yamaha R15 V4",
];

export function Products() {
  const [searchParams] = useSearchParams();
  const querySearch = searchParams.get("search") || "";
  const [products, setProducts] = useState([]);
  const [totalCount, setTotalCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Filter states
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [search, setSearch] = useState(querySearch);
  const [searchInput, setSearchInput] = useState(querySearch);
  const [selectedCategory, setSelectedCategory] = useState("All Categories");
  const [selectedVehicle, setSelectedVehicle] = useState("All Vehicles");

  // Inventory Edit Modal
  const [editProduct, setEditProduct] = useState(null);
  const [newStock, setNewStock] = useState("");
  const [stockReason, setStockReason] = useState("");
  const [stockSubmitting, setStockSubmitting] = useState(false);
  const [stockError, setStockError] = useState(null);

  // New Product Modal
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [editingSku, setEditingSku] = useState(null);
  const [feedback, setFeedback] = useState("");
  const [createData, setCreateData] = useState({
    sku: "",
    name: "",
    category: "Brakes",
    brand: "",
    vehicle_fitment: "Universal",
    price: "",
    description: "",
  });
  const [createSubmitting, setCreateSubmitting] = useState(false);
  const [createError, setCreateError] = useState(null);



  const [previousQuery, setPreviousQuery] = useState(querySearch);
  if (previousQuery !== querySearch) { setPreviousQuery(querySearch); setSearch(querySearch); setSearchInput(querySearch); setPage(1); }

  const fetchProducts = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params = {
        page,
        page_size: pageSize,
      };
      if (search.trim()) params.search = search.trim();
      if (selectedCategory !== "All Categories") params.category = selectedCategory;
      if (selectedVehicle !== "All Vehicles") params.vehicle = selectedVehicle;

      const res = await getProducts(params);
      setProducts(res.results || []);
      setTotalCount(res.count || 0);
    } catch (err) {
      setError(err.message || "Failed to load products catalogue.");
    } finally {
      setLoading(false);
    }
  }, [page, pageSize, search, selectedCategory, selectedVehicle]);

  const handleSearchSubmit = (e) => {
    e.preventDefault();
    setSearch(searchInput);
    setPage(1);
  };

  const handleStockUpdate = async (e) => {
    e.preventDefault();
    setStockSubmitting(true);
    setStockError(null);
    try {
      const qty = Number(newStock);
      if (!Number.isInteger(qty) || qty < 0) {
        throw new Error("Quantity must be a non-negative integer.");
      }
      await updateInventory(editProduct.sku, qty, stockReason.trim());
      setEditProduct(null);
      setFeedback(`Stock updated for ${editProduct.sku}.`);
      fetchProducts();
    } catch (err) {
      setStockError(err.message || "Failed to update stock.");
    } finally {
      setStockSubmitting(false);
    }
  };

  const handleCreateProduct = async (e) => {
    e.preventDefault();
    setCreateSubmitting(true);
    setCreateError(null);
    try {
      const p = parseFloat(createData.price);
      if (isNaN(p) || p <= 0) {
        throw new Error("Price must be a positive number.");
      }
      const payload = { ...createData, price: p.toFixed(2) };
      if (editingSku) await patchProduct(editingSku, payload);
      else await createProduct(payload);
      setFeedback(editingSku ? `Product ${editingSku} updated.` : `Product ${createData.sku} created.`);
      setEditingSku(null);
      setShowCreateModal(false);
      setCreateData({
        sku: "",
        name: "",
        category: "Brakes",
        brand: "",
        vehicle_fitment: "Universal",
        price: "",
        description: "",
      });
      fetchProducts();
    } catch (err) {
      setCreateError(err.message || "Failed to create product.");
    } finally {
      setCreateSubmitting(false);
    }
  };

  const totalPages = Math.ceil(totalCount / pageSize) || 1;

  useEffect(() => {
    // Loading state tracks this external API request.
    // oxlint-disable-next-line react/set-state-in-effect
    fetchProducts();
  }, [page, pageSize, search, selectedCategory, selectedVehicle, fetchProducts]);

  return (
    <div className="space-y-8">
      {/* Title & Actions */}
      <div className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1.5">
            <span className="w-2 h-2 rounded-full bg-success" />
            <span className="text-xs font-semibold uppercase tracking-wider text-secondary">
              Verified Inventory
            </span>
          </div>
          <h1 className="font-display text-3xl sm:text-4xl font-bold tracking-tight text-foreground">
            Product Catalogue
          </h1>
          <p className="text-sm text-secondary mt-1 max-w-xl">
            Manage your parts catalogue, stock availability, and dealer pricing.
          </p>
        </div>

        <button
          onClick={() => { setEditingSku(null); setCreateError(null); setCreateData({ sku: "", name: "", category: "Brakes", brand: "", vehicle_fitment: "Universal", price: "", description: "" }); setShowCreateModal(true); }}
          className="btn-primary text-sm shadow-xs self-start sm:self-auto flex items-center gap-2"
        >
          <Plus className="w-4 h-4" />
          <span>Add Product</span>
        </button>
      </div>

      {feedback && <div role="status" className="notice-success px-4 py-3 rounded-lg flex justify-between gap-3">{feedback}<button onClick={() => setFeedback("")} aria-label="Dismiss success message"><X size={16} /></button></div>}

      {/* Filter and Search Bar */}
      <div className="panel p-5 sm:p-6 rounded-xl border border-line space-y-4">
        <form onSubmit={handleSearchSubmit} className="flex gap-2 sm:gap-3">
          <div className="relative flex-1">
            <Search className="w-4.5 h-4.5 absolute left-3.5 top-3.5 text-secondary" />
            <input
              type="text"
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              aria-label="Search by SKU, part name, or brand"
              placeholder="Search by SKU, part name, or brand..."
              className="form-control w-full pl-10 pr-4 py-2.5 text-sm"
            />
          </div>
          <button
            type="submit"
            className="btn-primary text-xs px-5 py-2.5"
          >
            Search
          </button>
          {search && (
            <button
              type="button"
              onClick={() => {
                setSearchInput("");
                setSearch("");
                setPage(1);
              }}
              className="btn-ghost text-xs px-4"
            >
              Clear
            </button>
          )}
        </form>

        <div className="flex flex-wrap items-center gap-3 pt-3 border-t border-line">
          <div className="flex items-center gap-2">
            <span className="text-xs font-semibold uppercase tracking-wider text-secondary">
              Category:
            </span>
            <select
              aria-label="Product category"
              value={selectedCategory}
              onChange={(e) => {
                setSelectedCategory(e.target.value);
                setPage(1);
              }}
              className="form-control text-xs py-1.5 px-3"
            >
              {CATEGORIES.map((cat) => (
                <option key={cat} value={cat}>
                  {cat}
                </option>
              ))}
            </select>
          </div>

          <div className="flex items-center gap-2">
            <span className="text-xs font-semibold uppercase tracking-wider text-secondary">
              Fitment:
            </span>
            <select
              aria-label="Vehicle fitment"
              value={selectedVehicle}
              onChange={(e) => {
                setSelectedVehicle(e.target.value);
                setPage(1);
              }}
              className="form-control text-xs py-1.5 px-3"
            >
              {VEHICLES.map((v) => (
                <option key={v} value={v}>
                  {v}
                </option>
              ))}
            </select>
          </div>

          <div className="ml-auto flex items-center gap-2">
            <span className="text-xs font-semibold uppercase tracking-wider text-secondary">
              Rows:
            </span>
            <select
              aria-label="Products per page"
              value={pageSize}
              onChange={(e) => {
                setPageSize(Number(e.target.value));
                setPage(1);
              }}
              className="form-control text-xs py-1.5 px-3"
            >
              <option value={10}>10</option>
              <option value={20}>20</option>
              <option value={50}>50</option>
              <option value={100}>100</option>
            </select>
          </div>
        </div>
      </div>

      {/* Table Section */}
      <div className="panel rounded-xl border border-line overflow-hidden">
        {loading ? (
          <div className="p-6">
            <TableSkeleton rows={8} cols={6} />
          </div>
        ) : error ? (
          <div className="p-8 text-center text-danger">
            <AlertCircle className="w-8 h-8 mx-auto mb-2 text-danger" />
            <p role="alert" className="text-sm font-semibold">{error}</p>
            <button className="btn-secondary text-xs mt-3" onClick={fetchProducts}>Try again</button>
          </div>
        ) : products.length === 0 ? (
          <EmptyState
            title="No matching products"
            description="Try adjusting your filters or search keywords."
          />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm divide-y divide-line/60">
              <thead className="bg-subtle text-xs font-semibold text-secondary uppercase tracking-wider">
                <tr>
                  <th className="px-5 py-3.5 whitespace-nowrap">SKU</th>
                  <th className="px-5 py-3.5 min-w-[220px]">Product Name</th>
                  <th className="px-5 py-3.5 whitespace-nowrap">Category</th>
                  <th className="px-5 py-3.5 whitespace-nowrap">Vehicle Fitment</th>
                  <th className="px-5 py-3.5 whitespace-nowrap">Price</th>
                  <th className="px-5 py-3.5 whitespace-nowrap">Stock</th>
                  <th className="px-5 py-3.5 text-right whitespace-nowrap">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-line/60">
                {products.map((p) => (
                  <tr key={p.sku} className="hover:bg-surface transition-colors">
                    <td className="px-5 py-3.5 font-mono text-xs font-bold text-foreground whitespace-nowrap">
                      {p.sku}
                    </td>
                    <td className="px-5 py-3.5">
                      <div className="font-semibold text-foreground">{p.name}</div>
                      <div className="text-xs text-secondary">{p.brand}</div>
                    </td>
                    <td className="px-5 py-3.5 whitespace-nowrap">
                      <span className="px-2.5 py-0.5 rounded-full bg-subtle/60 text-xs font-medium text-foreground">
                        {p.category}
                      </span>
                    </td>
                    <td className="px-5 py-3.5 text-xs text-secondary whitespace-nowrap">
                      {p.vehicle_fitment}
                    </td>
                    <td className="px-5 py-3.5 font-semibold text-foreground whitespace-nowrap">
                      ₹{parseFloat(p.price || 0).toLocaleString("en-IN", {
                        minimumFractionDigits: 2,
                      })}
                    </td>
                    <td className="px-5 py-3.5 whitespace-nowrap">
                      <StockBadge stock={p.stock} />
                    </td>
                    <td className="px-5 py-3.5 text-right whitespace-nowrap">
                      <button className="btn-ghost text-xs mr-2" onClick={() => { setEditingSku(p.sku); setCreateData({ sku: p.sku, name: p.name, category: p.category, brand: p.brand || "", vehicle_fitment: p.vehicle_fitment, price: p.price, description: p.description || "" }); setCreateError(null); setShowCreateModal(true); }}>Edit</button>
                      <button
                        onClick={() => {
                          setEditProduct(p);
                          setNewStock(p.stock.toString());
                          setStockReason("");
                          setStockError(null);
                        }}
                        className="inline-flex items-center gap-1.5 text-xs font-semibold text-primary-hover bg-primary-soft hover:bg-subtle px-3.5 py-1.5 rounded-full transition-colors cursor-pointer"
                      >
                        <Edit3 className="w-3.5 h-3.5" />
                        <span>Adjust</span>
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Pagination Bar */}
        {!loading && totalCount > 0 && (
          <div className="px-6 py-4 border-t border-line bg-subtle/30 flex flex-col sm:flex-row items-center justify-between gap-3 text-xs text-secondary">
            <div>
              Showing <span className="font-bold text-foreground">{(page - 1) * pageSize + 1}</span> to{" "}
              <span className="font-bold text-foreground">
                {Math.min(page * pageSize, totalCount)}
              </span>{" "}
              of <span className="font-bold text-foreground">{totalCount}</span> parts
            </div>
            <div className="flex items-center gap-2">
              <button
                disabled={page <= 1}
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                className="btn-secondary text-xs px-3.5 py-1.5 disabled:opacity-40"
              >
                Previous
              </button>
              <span className="px-2 font-semibold text-foreground">
                Page {page} of {totalPages}
              </span>
              <button
                disabled={page >= totalPages}
                onClick={() => setPage((p) => p + 1)}
                className="btn-secondary text-xs px-3.5 py-1.5 disabled:opacity-40"
              >
                Next
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Adjust Inventory Modal */}
      {editProduct && (
        <Modal label="Adjust inventory" onClose={() => setEditProduct(null)} busy={stockSubmitting}>{(closeModal) => (
          <div className="panel bg-surface rounded-xl border border-line shadow-2xl max-w-md w-full p-6 sm:p-7 space-y-4">
            <div className="flex items-center justify-between border-b border-line pb-4">
              <div>
                <span className="text-[10px] font-bold uppercase tracking-widest text-primary">
                  STOCK ADJUSTMENT
                </span>
                <h3 className="font-display font-bold text-xl text-foreground">
                  {editProduct.sku}
                </h3>
              </div>
              <button
                aria-label="Close dialog"
                disabled={stockSubmitting}
                onClick={closeModal}
                className="p-1.5 rounded-full hover:bg-subtle text-secondary"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <p className="text-xs text-secondary -mt-1">
              {editProduct.name} ({editProduct.vehicle_fitment})
            </p>

            <form onSubmit={handleStockUpdate} className="space-y-4 pt-1">
              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-secondary mb-1.5">
                  New Stock Count (Units) *
                </label>
                <input
                  type="number"
                  min="0"
                  required
                  value={newStock}
                  onChange={(e) => setNewStock(e.target.value)}
                  className="form-control w-full text-sm font-semibold"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-secondary mb-1.5">
                  Adjustment Reason (Optional)
                </label>
                <input
                  type="text"
                  placeholder="e.g. Warehouse count audit, damaged stock"
                  value={stockReason}
                  onChange={(e) => setStockReason(e.target.value)}
                  className="form-control w-full text-sm"
                />
              </div>

              {stockError && (
                <div role="alert" className="p-3 bg-danger-soft text-danger text-xs font-medium rounded-xl border border-danger-line">
                  {stockError}
                </div>
              )}

              <div className="flex justify-end gap-3 pt-3">
                <button
                  type="button"
                  onClick={closeModal}
                  className="btn-secondary text-xs"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={stockSubmitting}
                  className="btn-primary text-xs disabled:opacity-50"
                >
                  {stockSubmitting ? "Updating..." : "Save Stock Count"}
                </button>
              </div>
            </form>
          </div>
        
        )}
        </Modal>
      )}

      {/* Create Product Modal */}
      {showCreateModal && (
        <Modal label={editingSku ? "Edit product" : "Create product"} onClose={() => setShowCreateModal(false)} busy={createSubmitting}>{(closeModal) => (
          <div className="panel bg-surface rounded-xl border border-line shadow-2xl max-w-lg w-full p-6 sm:p-7 space-y-4 max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between border-b border-line pb-4">
              <div>
                <span className="text-[10px] font-bold uppercase tracking-widest text-primary">
                  CATALOGUE EXPANSION
                </span>
                <h3 className="font-display font-bold text-xl text-foreground">
                  {editingSku ? "Edit product" : "Create product"}
                </h3>
              </div>
              <button
                aria-label="Close dialog"
                disabled={createSubmitting}
                onClick={closeModal}
                className="p-1.5 rounded-full hover:bg-subtle text-secondary"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleCreateProduct} className="space-y-4 pt-1">
              <div className="grid grid-cols-2 gap-3.5">
                <div>
                  <label className="block text-xs font-semibold uppercase tracking-wider text-secondary mb-1">
                    SKU Code *
                  </label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. BRK-9901"
                    readOnly={Boolean(editingSku)}
                    value={createData.sku}
                    onChange={(e) =>
                      setCreateData({ ...createData, sku: e.target.value.toUpperCase() })
                    }
                    className="form-control w-full text-sm font-mono uppercase"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold uppercase tracking-wider text-secondary mb-1">
                    Brand *
                  </label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. Endurance, Bosch"
                    value={createData.brand}
                    onChange={(e) => setCreateData({ ...createData, brand: e.target.value })}
                    className="form-control w-full text-sm"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-secondary mb-1">
                  Product Name *
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Disc Brake Pad Set Front"
                  value={createData.name}
                  onChange={(e) => setCreateData({ ...createData, name: e.target.value })}
                  className="form-control w-full text-sm"
                />
              </div>

              <div className="grid grid-cols-2 gap-3.5">
                <div>
                  <label className="block text-xs font-semibold uppercase tracking-wider text-secondary mb-1">
                    Category *
                  </label>
                  <select
                    value={createData.category}
                    onChange={(e) => setCreateData({ ...createData, category: e.target.value })}
                    className="form-control w-full text-sm"
                  >
                    {CATEGORIES.filter((c) => c !== "All Categories").map((c) => (
                      <option key={c} value={c}>
                        {c}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-semibold uppercase tracking-wider text-secondary mb-1">
                    Vehicle Fitment *
                  </label>
                  <select
                    value={createData.vehicle_fitment}
                    onChange={(e) =>
                      setCreateData({ ...createData, vehicle_fitment: e.target.value })
                    }
                    className="form-control w-full text-sm"
                  >
                    {VEHICLES.filter((v) => v !== "All Vehicles").map((v) => (
                      <option key={v} value={v}>
                        {v}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-secondary mb-1">
                  Price (₹ INR, excluding GST) *
                </label>
                <input
                  type="number"
                  step="0.01"
                  min="0.01"
                  required
                  placeholder="e.g. 1499.00"
                  value={createData.price}
                  onChange={(e) => setCreateData({ ...createData, price: e.target.value })}
                  className="form-control w-full text-sm font-semibold"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-secondary mb-1">
                  Description
                </label>
                <textarea
                  rows="2"
                  placeholder="Specifications, compatibility notes..."
                  value={createData.description}
                  onChange={(e) =>
                    setCreateData({ ...createData, description: e.target.value })
                  }
                  className="form-control w-full text-sm"
                />
              </div>

              {createError && (
                <div role="alert" className="p-3 bg-danger-soft text-danger text-xs font-medium rounded-xl border border-danger-line">
                  {createError}
                </div>
              )}

              <div className="flex justify-end gap-3 pt-3">
                <button
                  type="button"
                  onClick={closeModal}
                  className="btn-secondary text-xs"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={createSubmitting}
                  className="btn-primary text-xs disabled:opacity-50"
                >
                  {createSubmitting ? "Saving…" : "Save product"}
                </button>
              </div>
            </form>
          </div>
        
        )}
        </Modal>
      )}
    </div>
  );
}
