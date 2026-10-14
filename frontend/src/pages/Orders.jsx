import { Modal } from "../components/Modal";
import React, { useState, useEffect, useCallback } from "react";
import { useSearchParams } from "react-router-dom";
import {
  Plus,
  Eye,
  CheckCircle2,
  XCircle,
  Truck,
  PackageCheck,
  AlertCircle,
  X,
  Trash2,
} from "lucide-react";
import {
  getOrders,
  getOrder,
  createOrder,
  confirmOrder,
  cancelOrder,
  dispatchOrder,
  deliverOrder,
  getDealers,
} from "../services/api";
import { StatusBadge } from "../components/Badge";
import { TableSkeleton } from "../components/LoadingSkeleton";
import { EmptyState } from "../components/EmptyState";

const STATUS_FILTERS = [
  "ALL",
  "DRAFT",
  "CONFIRMED",
  "DISPATCHED",
  "DELIVERED",
  "CANCELLED",
];

export function Orders() {
  const [searchParams, setSearchParams] = useSearchParams();
  const targetOrderParam = searchParams.get("order");

  const [orders, setOrders] = useState([]);
  const [totalCount, setTotalCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const [page, setPage] = useState(1);
  const [statusFilter, setStatusFilter] = useState("ALL");

  // Selected Order Detail View
  const [selectedOrder, setSelectedOrder] = useState(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [actionError, setActionError] = useState(null);
  const [actionLoading, setActionLoading] = useState(false);

  // Create Order Modal
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [dealersList, setDealersList] = useState([]);
  const [newOrderDealerId, setNewOrderDealerId] = useState("");
  const [newOrderItems, setNewOrderItems] = useState([
    { sku: "", quantity: 1 },
  ]);
  const [createSubmitting, setCreateSubmitting] = useState(false);
  const [createError, setCreateError] = useState(null);





  const fetchOrders = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params = {
        page,
        page_size: 20,
      };
      if (statusFilter !== "ALL") {
        params.status = statusFilter;
      }
      const res = await getOrders(params);
      setOrders(res.results || []);
      setTotalCount(res.count || 0);
    } catch (err) {
      setError(err.message || "Failed to load orders.");
    } finally {
      setLoading(false);
    }
  }, [page, statusFilter]);

  const closeOrder = () => { setSelectedOrder(null); setSearchParams({}, { replace: true }); };

  const handleViewOrder = useCallback(async (orderNumber) => {
    setDetailLoading(true);
    setActionError(null);
    try {
      const res = await getOrder(orderNumber);
      setSelectedOrder(res);
    } catch (err) {
      setActionError(err.message || `Failed to fetch order ${orderNumber}`);
    } finally {
      setDetailLoading(false);
    }
  }, []);

  const handleTransition = async (action) => {
    if (!selectedOrder) return;
    setActionLoading(true);
    setActionError(null);
    try {
      let updated;
      if (action === "confirm") {
        updated = await confirmOrder(selectedOrder.order_number);
      } else if (action === "dispatch") {
        updated = await dispatchOrder(selectedOrder.order_number);
      } else if (action === "deliver") {
        updated = await deliverOrder(selectedOrder.order_number);
      } else if (action === "cancel") {
        updated = await cancelOrder(selectedOrder.order_number);
      }
      setSelectedOrder(updated);
      fetchOrders();
    } catch (err) {
      setActionError(err.message || `Failed to ${action} order.`);
    } finally {
      setActionLoading(false);
    }
  };

  const handleOpenCreateModal = async () => {
    setShowCreateModal(true);
    setCreateError(null);
    try {
      const dRes = await getDealers({ page_size: 50 });
      const dList = dRes.results || [];
      setDealersList(dList);
      if (dList.length > 0 && !newOrderDealerId) {
        setNewOrderDealerId(dList[0].id.toString());
      }
    } catch (err) {
      setCreateError(err.message || "Could not load dealer options.");
    }
  };

  const handleAddItemRow = () => {
    setNewOrderItems([...newOrderItems, { sku: "", quantity: 1 }]);
  };

  const handleRemoveItemRow = (idx) => {
    setNewOrderItems(newOrderItems.filter((_, i) => i !== idx));
  };

  const handleItemChange = (idx, field, val) => {
    const updated = [...newOrderItems];
    updated[idx][field] = field === "sku" ? val.toUpperCase() : parseInt(val, 10) || 1;
    setNewOrderItems(updated);
  };

  const handleCreateOrderSubmit = async (e) => {
    e.preventDefault();
    setCreateSubmitting(true);
    setCreateError(null);
    try {
      if (!newOrderDealerId) throw new Error("Please select a dealer.");
      if (newOrderItems.length === 0) throw new Error("Add at least one item line.");

      const seen = new Set();
      for (const item of newOrderItems) {
        if (!item.sku.trim()) throw new Error("SKU cannot be empty.");
        if (seen.has(item.sku.trim())) throw new Error(`Duplicate SKU ${item.sku} in order.`);
        seen.add(item.sku.trim());
      }

      const res = await createOrder({
        dealer_id: parseInt(newOrderDealerId, 10),
        items: newOrderItems.map((i) => ({ sku: i.sku.trim(), quantity: i.quantity })),
      });

      setShowCreateModal(false);
      setSelectedOrder(res);
      fetchOrders();
    } catch (err) {
      setCreateError(err.message || "Failed to create order.");
    } finally {
      setCreateSubmitting(false);
    }
  };

  const totalPages = Math.ceil(totalCount / 20) || 1;

  useEffect(() => {
    // Loading state tracks this external API request.
    // oxlint-disable-next-line react/set-state-in-effect
    fetchOrders();
  }, [page, statusFilter, fetchOrders]);
  useEffect(() => {
    if (targetOrderParam) {
      // Loading state tracks the linked order request.
      // oxlint-disable-next-line react/set-state-in-effect
      handleViewOrder(targetOrderParam);
    }
  }, [targetOrderParam, handleViewOrder]);

  return (
    <div className="space-y-8">
      {/* Title & Actions */}
      <div className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1.5">
            <span className="w-2 h-2 rounded-full bg-success" />
            <span className="text-xs font-semibold uppercase tracking-wider text-secondary">
              Automotive B2B Orders
            </span>
          </div>
          <h1 className="font-display text-3xl sm:text-4xl font-bold tracking-tight text-foreground">
            Distributor Orders
          </h1>
          <p className="text-sm text-secondary mt-1 max-w-xl">
            Manage dealer orders from draft to delivery. Stock is reserved on confirmation.
          </p>
        </div>

        <button
          onClick={handleOpenCreateModal}
          className="btn-primary text-sm shadow-xs self-start sm:self-auto flex items-center gap-2"
        >
          <Plus className="w-4 h-4" />
          <span>New Draft Order</span>
        </button>
      </div>
      <div className="flex flex-wrap items-center gap-2">
        {STATUS_FILTERS.map((st) => (
          <button
            key={st}
            onClick={() => {
              setStatusFilter(st);
              setPage(1);
            }}
            aria-pressed={statusFilter === st}
            className={`px-4 py-2 rounded-lg text-xs font-semibold transition-all ${
              statusFilter === st
                ? "bg-primary text-on-primary shadow-xs"
                : "bg-surface text-secondary hover:bg-subtle hover:text-foreground border border-line"
            }`}
          >
            {st === "ALL" ? "All orders" : st.charAt(0) + st.slice(1).toLowerCase()}
          </button>
        ))}
      </div>

      {/* Table Section */}
      <div className="panel rounded-xl border border-line overflow-hidden">
        {loading ? (
          <div className="p-6">
            <TableSkeleton rows={8} cols={7} />
          </div>
        ) : error ? (
          <div className="p-8 text-center text-danger">
            <AlertCircle className="w-8 h-8 mx-auto mb-2 text-danger" />
            <p role="alert" className="text-sm font-semibold">{error}</p>
            <button className="btn-secondary text-xs mt-3" onClick={fetchOrders}>Try again</button>
          </div>
        ) : orders.length === 0 ? (
          <EmptyState
            title="No orders found"
            description="Create an order or place one via the GenAI Assistant."
          />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm divide-y divide-line/60">
              <thead className="bg-subtle text-xs font-semibold text-secondary uppercase tracking-wider">
                <tr>
                  <th className="px-5 py-3.5 whitespace-nowrap">Order Number</th>
                  <th className="px-5 py-3.5 whitespace-nowrap">Dealer ID</th>
                  <th className="px-5 py-3.5 whitespace-nowrap">Created</th>
                  <th className="px-5 py-3.5 whitespace-nowrap">Status</th>
                  <th className="px-5 py-3.5 whitespace-nowrap">Items</th>
                  <th className="px-5 py-3.5 whitespace-nowrap">Subtotal</th>
                  <th className="px-5 py-3.5 whitespace-nowrap">18% GST</th>
                  <th className="px-5 py-3.5 whitespace-nowrap">Grand Total</th>
                  <th className="px-5 py-3.5 text-right whitespace-nowrap">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-line/60">
                {orders.map((o) => (
                  <tr key={o.order_number} className="hover:bg-surface transition-colors">
                    <td className="px-5 py-3.5 font-mono text-xs font-bold text-foreground whitespace-nowrap">
                      {o.order_number}
                    </td>
                    <td className="px-5 py-3.5 text-xs text-secondary whitespace-nowrap">
                      Dealer #{o.dealer_id}
                    </td>
                    <td className="px-5 py-3.5 text-xs text-secondary whitespace-nowrap">{new Date(o.created_at).toLocaleDateString("en-IN")}</td>
                    <td className="px-5 py-3.5 whitespace-nowrap">
                      <StatusBadge status={o.status} />
                    </td>
                    <td className="px-5 py-3.5 text-xs text-secondary whitespace-nowrap">
                      {o.items?.length || 0} line(s)
                    </td>
                    <td className="px-5 py-3.5 text-xs font-semibold text-secondary whitespace-nowrap">
                      ₹{parseFloat(o.subtotal || 0).toLocaleString("en-IN", {
                        minimumFractionDigits: 2,
                      })}
                    </td>
                    <td className="px-5 py-3.5 text-xs font-semibold text-secondary whitespace-nowrap">
                      ₹{parseFloat(o.tax_total || 0).toLocaleString("en-IN", {
                        minimumFractionDigits: 2,
                      })}
                    </td>
                    <td className="px-5 py-3.5 font-bold text-foreground whitespace-nowrap">
                      ₹{parseFloat(o.grand_total || 0).toLocaleString("en-IN", {
                        minimumFractionDigits: 2,
                      })}
                    </td>
                    <td className="px-5 py-3.5 text-right whitespace-nowrap">
                      <button
                        onClick={() => handleViewOrder(o.order_number)}
                        className="inline-flex items-center gap-1.5 text-xs font-semibold text-primary-hover bg-primary-soft hover:bg-subtle px-3.5 py-1.5 rounded-full transition-colors cursor-pointer"
                      >
                        <Eye className="w-3.5 h-3.5" />
                        <span>Inspect</span>
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
              Showing <span className="font-bold text-foreground">{orders.length}</span> of{" "}
              <span className="font-bold text-foreground">{totalCount}</span> orders
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

      {detailLoading && <div role="status" className="panel p-4"><TableSkeleton rows={2} cols={3} /><span className="text-sm text-secondary">Loading order details…</span></div>}
      {actionError && !selectedOrder && <div role="alert" className="notice-error p-4 rounded-lg">{actionError}</div>}

      {/* Inspect Order Modal */}
      {selectedOrder && (
        <Modal label="Order details" onClose={closeOrder} busy={actionLoading}>{(closeModal) => (
          <div className="panel bg-surface rounded-xl border border-line shadow-2xl max-w-2xl w-full p-6 sm:p-7 space-y-5 max-h-[90vh] overflow-y-auto">
            {/* Modal Header */}
            <div className="flex items-center justify-between border-b border-line pb-4">
              <div>
                <div className="flex items-center gap-2.5">
                  <h3 className="font-display font-bold text-2xl text-foreground">
                    {selectedOrder.order_number}
                  </h3>
                  <StatusBadge status={selectedOrder.status} />
                </div>
                <p className="text-xs text-secondary mt-1">
                  Dealer ID: #{selectedOrder.dealer_id} · Created:{" "}
                  {new Date(selectedOrder.created_at).toLocaleString()}
                </p>
              </div>
              <button
                aria-label="Close dialog"
                disabled={actionLoading}
                onClick={closeModal}
                className="p-1.5 rounded-full hover:bg-subtle text-secondary"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Error Message if Action Failed */}
            {actionError && (
              <div role="alert" className="p-3 bg-danger-soft text-danger text-xs font-semibold rounded-xl border border-danger-line flex items-center gap-2">
                <AlertCircle className="w-4 h-4 shrink-0" />
                <span>{actionError}</span>
              </div>
            )}

            {/* Items Table */}
            <div>
              <div className="text-[11px] font-bold uppercase tracking-widest text-secondary mb-2">
                Order Line Items
              </div>
              <div className="border border-line rounded-lg overflow-x-auto bg-surface">
                <table className="w-full text-left text-xs">
                  <thead className="bg-subtle/50 text-secondary border-b border-line font-semibold uppercase tracking-wider">
                    <tr>
                      <th className="px-3.5 py-2.5">SKU</th>
                      <th className="px-3.5 py-2.5">Part Description</th>
                      <th className="px-3.5 py-2.5 text-center">Qty</th>
                      <th className="px-3.5 py-2.5 text-right">Unit Price</th>
                      <th className="px-3.5 py-2.5 text-right">Subtotal</th>
                      <th className="px-3.5 py-2.5 text-right">18% GST</th>
                      <th className="px-3.5 py-2.5 text-right font-bold">Total</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-line/60">
                    {(selectedOrder.items || []).map((it, idx) => (
                      <tr key={idx} className="hover:bg-subtle/20">
                        <td className="px-3.5 py-2.5 font-mono font-bold text-foreground">
                          {it.sku}
                        </td>
                        <td className="px-3.5 py-2.5 text-foreground font-medium">
                          {it.name}
                        </td>
                        <td className="px-3.5 py-2.5 text-center font-bold text-foreground">
                          {it.quantity}
                        </td>
                        <td className="px-3.5 py-2.5 text-right text-secondary">
                          ₹{parseFloat(it.unit_price).toFixed(2)}
                        </td>
                        <td className="px-3.5 py-2.5 text-right text-secondary">
                          ₹{parseFloat(it.line_subtotal).toFixed(2)}
                        </td>
                        <td className="px-3.5 py-2.5 text-right text-secondary">
                          ₹{parseFloat(it.line_tax).toFixed(2)}
                        </td>
                        <td className="px-3.5 py-2.5 text-right font-bold text-foreground">
                          ₹{parseFloat(it.line_total).toFixed(2)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Financial Totals Card */}
            <div className="bg-surface rounded-lg p-4 sm:p-5 border border-line space-y-2 text-xs">
              <div className="flex justify-between text-secondary">
                <span>Subtotal (Net Amount):</span>
                <span className="font-semibold text-foreground">
                  ₹{parseFloat(selectedOrder.subtotal).toFixed(2)}
                </span>
              </div>
              <div className="flex justify-between text-secondary">
                <span>GST (18%):</span>
                <span className="font-semibold text-foreground">
                  ₹{parseFloat(selectedOrder.tax_total).toFixed(2)}
                </span>
              </div>
              <div className="flex justify-between text-foreground font-bold text-sm pt-2.5 border-t border-line">
                <span className="font-display">Grand Total:</span>
                <span className="font-display text-base text-primary">
                  ₹{parseFloat(selectedOrder.grand_total).toFixed(2)}
                </span>
              </div>
            </div>

            {/* Lifecycle Action Buttons */}
            <div className="border-t border-line pt-4 flex flex-wrap items-center justify-between gap-3">
              <div className="text-xs text-secondary">
                Lifecycle State: <span className="font-bold text-foreground">{selectedOrder.status}</span>
              </div>

              <div className="flex flex-wrap items-center gap-2">
                {selectedOrder.status === "DRAFT" && (
                  <>
                    <button
                      onClick={() => handleTransition("confirm")}
                      disabled={actionLoading}
                      className="inline-flex items-center gap-1.5 px-4 py-2 rounded-full text-xs font-semibold bg-primary hover:bg-primary-hover text-on-primary shadow-xs disabled:opacity-50"
                    >
                      <CheckCircle2 className="w-3.5 h-3.5" />
                      <span>Confirm & Deduct Stock</span>
                    </button>
                    <button
                      onClick={() => handleTransition("cancel")}
                      disabled={actionLoading}
                      className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-full text-xs font-semibold bg-danger-soft hover:bg-subtle text-danger border border-danger-line disabled:opacity-50"
                    >
                      <XCircle className="w-3.5 h-3.5" />
                      <span>Cancel Draft</span>
                    </button>
                  </>
                )}

                {selectedOrder.status === "CONFIRMED" && (
                  <>
                    <button
                      onClick={() => handleTransition("dispatch")}
                      disabled={actionLoading}
                      className="inline-flex items-center gap-1.5 px-4 py-2 rounded-full text-xs font-semibold bg-primary hover:bg-primary-hover text-on-primary shadow-xs disabled:opacity-50"
                    >
                      <Truck className="w-3.5 h-3.5" />
                      <span>Dispatch Order</span>
                    </button>
                    <button
                      onClick={() => handleTransition("cancel")}
                      disabled={actionLoading}
                      className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-full text-xs font-semibold bg-danger-soft hover:bg-subtle text-danger border border-danger-line disabled:opacity-50"
                    >
                      <XCircle className="w-3.5 h-3.5" />
                      <span>Cancel & Restore Stock</span>
                    </button>
                  </>
                )}

                {selectedOrder.status === "DISPATCHED" && (
                  <button
                    onClick={() => handleTransition("deliver")}
                    disabled={actionLoading}
                    className="inline-flex items-center gap-1.5 px-4 py-2 rounded-full text-xs font-semibold bg-primary hover:bg-primary-hover text-on-primary shadow-xs disabled:opacity-50"
                  >
                    <PackageCheck className="w-3.5 h-3.5" />
                    <span>Mark as Delivered</span>
                  </button>
                )}

                <button
                  type="button"
                  onClick={closeModal}
                  className="btn-secondary text-xs px-4"
                >
                  Close
                </button>
              </div>
            </div>
          </div>
        
        )}
        </Modal>
      )}

      {/* New Draft Order Modal */}
      {showCreateModal && (
        <Modal label="Create draft order" onClose={() => setShowCreateModal(false)} busy={createSubmitting}>{(closeModal) => (
          <div className="panel bg-surface rounded-xl border border-line shadow-2xl max-w-lg w-full p-6 sm:p-7 space-y-4 max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between border-b border-line pb-4">
              <div>
                <span className="text-[10px] font-bold uppercase tracking-widest text-primary">
                  ORDER CREATION
                </span>
                <h3 className="font-display font-bold text-xl text-foreground">
                  Create New Draft Order
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

            <form onSubmit={handleCreateOrderSubmit} className="space-y-4 pt-1">
              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-secondary mb-1.5">
                  Select Dealer Partner *
                </label>
                <select
                  value={newOrderDealerId}
                  onChange={(e) => setNewOrderDealerId(e.target.value)}
                  className="form-control w-full text-sm font-medium"
                >
                  {dealersList.map((d) => (
                    <option key={d.id} value={d.id}>
                      {d.dealer_code} — {d.name} ({d.city})
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <div className="flex items-center justify-between mb-2">
                  <label className="text-xs font-semibold uppercase tracking-wider text-secondary">
                    Order Items *
                  </label>
                  <button
                    type="button"
                    onClick={handleAddItemRow}
                    className="text-xs text-primary hover:text-primary-hover font-bold flex items-center gap-1"
                  >
                    <Plus className="w-3.5 h-3.5" />
                    <span>Add Item Line</span>
                  </button>
                </div>

                <div className="space-y-2.5">
                  {newOrderItems.map((item, idx) => (
                    <div key={idx} className="flex gap-2.5 items-center">
                      <input
                        aria-label={`Item ${idx + 1} SKU`}
                        type="text"
                        placeholder="SKU (e.g. BRK-1044)"
                        required
                        value={item.sku}
                        onChange={(e) => handleItemChange(idx, "sku", e.target.value)}
                        className="form-control flex-1 text-sm font-mono uppercase"
                      />
                      <input
                        aria-label={`Item ${idx + 1} quantity`}
                        type="number"
                        min="1"
                        required
                        placeholder="Qty"
                        value={item.quantity}
                        onChange={(e) =>
                          handleItemChange(idx, "quantity", e.target.value)
                        }
                        className="form-control w-24 text-sm font-bold text-center"
                      />
                      {newOrderItems.length > 1 && (
                        <button
                          type="button"
                          onClick={() => handleRemoveItemRow(idx)}
                          className="p-2 text-danger hover:bg-danger-soft rounded-full transition-colors"
                          title="Remove item"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      )}
                    </div>
                  ))}
                </div>
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
                  {createSubmitting ? "Creating..." : "Save Draft Order"}
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
