/**
 * VIKMO DealerDesk API Service Layer
 * Connects React frontend directly to the Django REST API endpoints.
 */

const BASE_URL = import.meta.env.VITE_API_BASE_URL || "";

async function request(endpoint, options = {}) {
  const url = `${BASE_URL}${endpoint}`;
  const headers = {
    "Content-Type": "application/json",
    ...options.headers,
  };

  const controller = new AbortController();
  const timeoutMs = options.timeout || 30000;
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  const config = {
    ...options,
    headers,
    signal: options.signal || controller.signal,
  };

  try {
    const res = await fetch(url, config);
    clearTimeout(timeoutId);
    const contentType = res.headers.get("content-type");
    let data = null;

    if (contentType && contentType.includes("application/json")) {
      data = await res.json();
    } else {
      data = await res.text();
    }

    if (!res.ok) {
      const errorMsg =
        (data && data.error && data.error.message) ||
        (data && data.detail) ||
        (typeof data === "string" ? data : `Request failed with status ${res.status}`);
      const details = data?.error?.details;
      const validation = Array.isArray(details) ? details.map(item => `${item.field}: ${item.error}`).join("; ") : "";
      const err = new Error(validation ? `${errorMsg} — ${validation}` : errorMsg);
      err.status = res.status;
      err.data = data;
      throw err;
    }

    return data;
  } catch (error) {
    clearTimeout(timeoutId);
    if (error.name === "AbortError") {
      error.message = "Request timed out. The server took too long to respond.";
    } else if (!error.status) {
      error.message = error.message || "Network error. Please check backend connection.";
    }
    throw error;
  }
}

// System Health
export const getHealth = () => request("/api/health/");

// Products
export const getProducts = (params = {}) => {
  const query = new URLSearchParams();
  if (params.page) query.set("page", params.page);
  if (params.page_size) query.set("page_size", params.page_size);
  if (params.search) query.set("search", params.search);
  if (params.category) query.set("category", params.category);
  if (params.vehicle) query.set("vehicle", params.vehicle);

  const qs = query.toString();
  return request(`/api/products/${qs ? `?${qs}` : ""}`);
};

export const getProduct = (sku) => request(`/api/products/${encodeURIComponent(sku)}/`);

export const createProduct = (data) =>
  request("/api/products/", {
    method: "POST",
    body: JSON.stringify(data),
  });

export const patchProduct = (sku, data) =>
  request(`/api/products/${encodeURIComponent(sku)}/`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });

export const updateInventory = (sku, quantity, reason = "") =>
  request(`/api/inventory/${encodeURIComponent(sku)}/`, {
    method: "PUT",
    body: JSON.stringify({ quantity, reason }),
  });

// Dealers
export const getDealers = (params = {}) => {
  const query = new URLSearchParams();
  if (params.page) query.set("page", params.page);
  if (params.page_size) query.set("page_size", params.page_size);

  const qs = query.toString();
  return request(`/api/dealers/${qs ? `?${qs}` : ""}`);
};

export const getDealer = (id) => request(`/api/dealers/${id}/`);

export const createDealer = (data) =>
  request("/api/dealers/", {
    method: "POST",
    body: JSON.stringify(data),
  });

// Orders
export const getOrders = (params = {}) => {
  const query = new URLSearchParams();
  if (params.page) query.set("page", params.page);
  if (params.page_size) query.set("page_size", params.page_size);
  if (params.dealer_id) query.set("dealer_id", params.dealer_id);
  if (params.status) query.set("status", params.status);

  const qs = query.toString();
  return request(`/api/orders/${qs ? `?${qs}` : ""}`);
};

export const getOrder = (orderNumber) => request(`/api/orders/${encodeURIComponent(orderNumber)}/`);

export const createOrder = (orderData, idempotencyKey = null) => {
  const headers = {};
  if (idempotencyKey) {
    headers["Idempotency-Key"] = idempotencyKey;
  }
  return request("/api/orders/", {
    method: "POST",
    headers,
    body: JSON.stringify(orderData),
  });
};

export const confirmOrder = (orderNumber) =>
  request(`/api/orders/${encodeURIComponent(orderNumber)}/confirm/`, {
    method: "POST",
  });

export const dispatchOrder = (orderNumber) =>
  request(`/api/orders/${encodeURIComponent(orderNumber)}/dispatch/`, {
    method: "POST",
  });

export const deliverOrder = (orderNumber) =>
  request(`/api/orders/${encodeURIComponent(orderNumber)}/deliver/`, {
    method: "POST",
  });

export const cancelOrder = (orderNumber) =>
  request(`/api/orders/${encodeURIComponent(orderNumber)}/cancel/`, {
    method: "POST",
  });

// Assistant
export const sendAssistantMessage = ({ sessionId, dealerId, message }) =>
  request("/api/assistant/chat/", {
    method: "POST",
    body: JSON.stringify({
      session_id: sessionId,
      dealer_id: dealerId,
      message,
    }),
  });

// Forecasting
export const getReorderSuggestions = () => request("/api/reorder-suggestions/");

export const getForecast = (sku) => request(`/api/forecast/${encodeURIComponent(sku)}/`);

// Supplier Sync
export const triggerSupplierSync = () =>
  request("/api/sync/supplier/", {
    method: "POST",
  });
