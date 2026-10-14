import { Modal } from "../components/Modal";
import React, { useState, useEffect, useCallback } from "react";
import { Link } from "react-router-dom";
import {
  Plus,
  Bot,
  MapPin,
  Phone,
  Mail,
  X,
  AlertCircle,
} from "lucide-react";
import { getDealers, createDealer } from "../services/api";
import { TableSkeleton } from "../components/LoadingSkeleton";
import { EmptyState } from "../components/EmptyState";

export function Dealers() {
  const [dealers, setDealers] = useState([]);
  const [totalCount, setTotalCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [feedback, setFeedback] = useState("");
  const [search, setSearch] = useState("");

  const [page, setPage] = useState(1);
  const pageSize = 25;

  // Create Dealer Modal
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [createData, setCreateData] = useState({
    dealer_code: "",
    name: "",
    city: "Bengaluru",
    phone: "",
    email: "",
    gstin: "",
    credit_limit: "500000.00",
  });
  const [createSubmitting, setCreateSubmitting] = useState(false);
  const [createError, setCreateError] = useState(null);



  const fetchDealers = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await getDealers({ page, page_size: pageSize });
      setDealers(res.results || []);
      setTotalCount(res.count || 0);
    } catch (err) {
      setError(err.message || "Failed to load dealers list.");
    } finally {
      setLoading(false);
    }
  }, [page, pageSize]);

  const handleCreateDealer = async (e) => {
    e.preventDefault();
    setCreateSubmitting(true);
    setCreateError(null);
    try {
      await createDealer(createData);
      setShowCreateModal(false);
      setFeedback(`Dealer ${createData.name} registered.`);
      setCreateData({
        dealer_code: "",
        name: "",
        city: "Bengaluru",
        phone: "",
        email: "",
        gstin: "",
        credit_limit: "500000.00",
      });
      fetchDealers();
    } catch (err) {
      setCreateError(err.message || "Failed to create dealer.");
    } finally {
      setCreateSubmitting(false);
    }
  };

  const filteredDealers = dealers.filter(dealer => [dealer.name, dealer.dealer_code, dealer.city, dealer.email].some(value => String(value || "").toLowerCase().includes(search.toLowerCase().trim())));

  const totalPages = Math.ceil(totalCount / pageSize) || 1;

  useEffect(() => {
    // Loading state tracks this external API request.
    // oxlint-disable-next-line react/set-state-in-effect
    fetchDealers();
  }, [page, pageSize, fetchDealers]);

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1.5">
            <span className="w-2 h-2 rounded-full bg-success" />
            <span className="text-xs font-semibold uppercase tracking-wider text-secondary">
              Distribution Partners
            </span>
          </div>
          <h1 className="font-display text-3xl sm:text-4xl font-bold tracking-tight text-foreground">
            Authorized Dealers
          </h1>
          <p className="text-sm text-secondary mt-1 max-w-xl">
            Manage distributor network, contact profiles, and approved commercial credit lines across South India.
          </p>
        </div>

        <button
          onClick={() => { setCreateError(null); setShowCreateModal(true); }}
          className="btn-primary text-sm shadow-xs self-start sm:self-auto flex items-center gap-2"
        >
          <Plus className="w-4 h-4" />
          <span>Add Dealer</span>
        </button>
      </div>

      {feedback && <div role="status" className="notice-success px-4 py-3 rounded-lg flex justify-between gap-3">{feedback}<button onClick={() => setFeedback("")} aria-label="Dismiss success message"><X size={16} /></button></div>}
      <div className="flex flex-wrap gap-3 items-center"><input className="form-control w-full sm:w-80 text-sm" aria-label="Search dealers on this page" placeholder="Search name, code, city, or email…" value={search} onChange={event => setSearch(event.target.value)} /><span className="text-xs text-secondary">Search this page · {filteredDealers.length} matches</span></div>

      {/* Content Section */}
      <div className="panel rounded-xl border border-line overflow-hidden">
        {loading ? (
          <div className="p-6">
            <TableSkeleton rows={6} cols={5} />
          </div>
        ) : error ? (
          <div className="p-8 text-center text-danger">
            <AlertCircle className="w-8 h-8 mx-auto mb-2 text-danger" />
            <p role="alert" className="text-sm font-semibold">{error}</p>
            <button className="btn-secondary text-xs mt-3" onClick={fetchDealers}>Try again</button>
          </div>
        ) : filteredDealers.length === 0 ? (
          <EmptyState
            title="No dealers found"
            description="Try another search or register a new dealer."
          />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm divide-y divide-line/60">
              <thead className="bg-subtle text-xs font-semibold text-secondary uppercase tracking-wider">
                <tr>
                  <th className="px-5 py-3.5 whitespace-nowrap">Dealer Code</th>
                  <th className="px-5 py-3.5 min-w-[180px]">Dealer Name</th>
                  <th className="px-5 py-3.5 whitespace-nowrap">Location</th>
                  <th className="px-5 py-3.5 min-w-[200px]">Contact Details</th>
                  <th className="px-5 py-3.5 whitespace-nowrap">GSTIN</th>
                  <th className="px-5 py-3.5 whitespace-nowrap">Credit Limit</th>
                  <th className="px-5 py-3.5 text-right whitespace-nowrap">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-line/60">
                {filteredDealers.map((d) => (
                  <tr key={d.id} className="hover:bg-surface transition-colors">
                    <td className="px-5 py-3.5 font-mono text-xs font-bold text-foreground whitespace-nowrap">
                      {d.dealer_code}
                    </td>
                    <td className="px-5 py-3.5 font-semibold text-foreground">
                      {d.name}
                    </td>
                    <td className="px-5 py-3.5 text-xs text-secondary whitespace-nowrap">
                      <div className="flex items-center gap-1.5">
                        <MapPin className="w-3.5 h-3.5 text-primary" />
                        <span>{d.city || "South India"}</span>
                      </div>
                    </td>
                    <td className="px-5 py-3.5 text-xs text-secondary">
                      <div className="space-y-0.5">
                        {d.phone && (
                          <div className="flex items-center gap-1.5 text-secondary">
                            <Phone className="w-3 h-3 text-secondary" />
                            <span>{d.phone}</span>
                          </div>
                        )}
                        {d.email && (
                          <div className="flex items-center gap-1.5 text-secondary">
                            <Mail className="w-3 h-3 text-secondary" />
                            <span>{d.email}</span>
                          </div>
                        )}
                      </div>
                    </td>
                    <td className="px-5 py-3.5 font-mono text-xs text-secondary whitespace-nowrap">
                      {d.gstin || "—"}
                    </td>
                    <td className="px-5 py-3.5 font-semibold text-foreground whitespace-nowrap">
                      ₹{parseFloat(d.credit_limit || 0).toLocaleString("en-IN", {
                        minimumFractionDigits: 2,
                      })}
                    </td>
                    <td className="px-5 py-3.5 text-right whitespace-nowrap">
                      <Link
                        to={`/assistant?dealer_id=${d.id}`}
                        className="inline-flex items-center gap-1.5 text-xs font-semibold text-primary-hover bg-primary-soft hover:bg-subtle px-3.5 py-1.5 rounded-full transition-colors"
                      >
                        <Bot className="w-3.5 h-3.5" />
                        <span>Chat as Dealer</span>
                      </Link>
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
              Showing <span className="font-bold text-foreground">{dealers.length}</span> of{" "}
              <span className="font-bold text-foreground">{totalCount}</span> dealers
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

      {/* Create Dealer Modal */}
      {showCreateModal && (
        <Modal label="Create dealer" onClose={() => setShowCreateModal(false)} busy={createSubmitting}>{(closeModal) => (
          <div className="panel bg-surface rounded-xl border border-line shadow-2xl max-w-lg w-full p-6 sm:p-7 space-y-4 max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between border-b border-line pb-4">
              <div>
                <span className="text-[10px] font-bold uppercase tracking-widest text-primary">
                  NETWORK ONBOARDING
                </span>
                <h3 className="font-display font-bold text-xl text-foreground">
                  Register Authorized Dealer
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

            <form onSubmit={handleCreateDealer} className="space-y-4 pt-1">
              <div className="grid grid-cols-2 gap-3.5">
                <div>
                  <label className="block text-xs font-semibold uppercase tracking-wider text-secondary mb-1">
                    Dealer Code *
                  </label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. DLR-8820"
                    value={createData.dealer_code}
                    onChange={(e) =>
                      setCreateData({
                        ...createData,
                        dealer_code: e.target.value.toUpperCase(),
                      })
                    }
                    className="form-control w-full text-sm font-mono uppercase"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold uppercase tracking-wider text-secondary mb-1">
                    City / Hub *
                  </label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. Bengaluru, Chennai"
                    value={createData.city}
                    onChange={(e) =>
                      setCreateData({ ...createData, city: e.target.value })
                    }
                    className="form-control w-full text-sm"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-secondary mb-1">
                  Dealer Name / Firm *
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Cauvery Auto Spares"
                  value={createData.name}
                  onChange={(e) =>
                    setCreateData({ ...createData, name: e.target.value })
                  }
                  className="form-control w-full text-sm"
                />
              </div>

              <div className="grid grid-cols-2 gap-3.5">
                <div>
                  <label className="block text-xs font-semibold uppercase tracking-wider text-secondary mb-1">
                    Phone Number
                  </label>
                  <input
                    type="tel"
                    placeholder="+91 98765 43210"
                    value={createData.phone}
                    onChange={(e) =>
                      setCreateData({ ...createData, phone: e.target.value })
                    }
                    className="form-control w-full text-sm"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold uppercase tracking-wider text-secondary mb-1">
                    Email Address
                  </label>
                  <input
                    type="email"
                    placeholder="dealer@example.com"
                    value={createData.email}
                    onChange={(e) =>
                      setCreateData({ ...createData, email: e.target.value })
                    }
                    className="form-control w-full text-sm"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3.5">
                <div>
                  <label className="block text-xs font-semibold uppercase tracking-wider text-secondary mb-1">
                    GSTIN (15 Digits)
                  </label>
                  <input
                    type="text"
                    placeholder="29AAAAA0000A1Z5"
                    value={createData.gstin}
                    onChange={(e) =>
                      setCreateData({
                        ...createData,
                        gstin: e.target.value.toUpperCase(),
                      })
                    }
                    className="form-control w-full text-sm font-mono uppercase"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold uppercase tracking-wider text-secondary mb-1">
                    Credit Limit (₹ INR) *
                  </label>
                  <input
                    type="number"
                    step="1000"
                    min="0"
                    required
                    placeholder="500000.00"
                    value={createData.credit_limit}
                    onChange={(e) =>
                      setCreateData({ ...createData, credit_limit: e.target.value })
                    }
                    className="form-control w-full text-sm font-semibold"
                  />
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
                  {createSubmitting ? "Onboarding..." : "Register Dealer"}
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
