import { apiGet, apiPatch, apiPost } from "./client";

export function createOrder(payload) {
  return apiPost("/api/orders", payload);
}

export function fetchOrders(sessionId) {
  return apiGet("/api/orders", { sessionId });
}

export function fetchOrder(orderNumber) {
  return apiGet(`/api/orders/${orderNumber}`);
}

export function fetchAdminOrders() {
  return apiGet("/api/admin/orders");
}

export function updateOrderStatus(orderId, status) {
  return apiPatch(`/api/admin/orders/${orderId}/status`, { status });
}
