import React from "react";

export function StatusBadge({ status }) {
  const statusConfig = {
    DRAFT: {
      bg: "bg-warning-soft text-warning-ink border-warning-line",
      label: "Draft",
      dot: "bg-warning",
    },
    CONFIRMED: {
      bg: "bg-primary-soft text-primary border-primary-line",
      label: "Confirmed",
      dot: "bg-primary",
    },
    DISPATCHED: {
      bg: "bg-info-soft text-info border-info-line",
      label: "Dispatched",
      dot: "bg-info",
    },
    DELIVERED: {
      bg: "bg-success-soft text-success-ink border-success-line",
      label: "Delivered",
      dot: "bg-success",
    },
    CANCELLED: {
      bg: "bg-danger-soft text-danger border-danger-line",
      label: "Cancelled",
      dot: "bg-danger",
    },
  };

  const config = statusConfig[status] || {
    bg: "bg-surface text-secondary border-line",
    label: status,
    dot: "bg-secondary",
  };

  return (
    <span
      className={`inline-flex items-center gap-1.5 px-3 py-0.5 rounded-full text-xs font-medium border ${config.bg}`}
    >
      <span className={`w-1.5 h-1.5 rounded-full ${config.dot}`} />
      <span>{config.label}</span>
    </span>
  );
}

export function StockBadge({ stock }) {
  if (stock === 0) {
    return (
      <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-danger-soft text-danger border border-danger-line">
        <span className="w-1.5 h-1.5 rounded-full bg-danger" />
        Out of Stock
      </span>
    );
  }
  if (stock < 20) {
    return (
      <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-warning-soft text-warning-ink border border-warning-line">
        <span className="w-1.5 h-1.5 rounded-full bg-warning" />
        Low ({stock})
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-success-soft text-success-ink border border-success-line">
      <span className="w-1.5 h-1.5 rounded-full bg-success" />
      {stock} units
    </span>
  );
}
