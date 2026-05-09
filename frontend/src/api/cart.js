import { apiDelete, apiGet, apiPost, apiPut } from "./client";

export function fetchCart(sessionId) {
  return apiGet("/api/cart", { sessionId });
}

export function addCartItem(sessionId, productId, quantity = 1) {
  return apiPost("/api/cart/items", {
    session_id: sessionId,
    product_id: productId,
    quantity,
  });
}

export function updateCartItem(sessionId, cartItemId, quantity) {
  return apiPut(`/api/cart/items/${cartItemId}`, {
    session_id: sessionId,
    quantity,
  });
}

export function removeCartItem(sessionId, cartItemId) {
  return apiDelete(`/api/cart/items/${cartItemId}?sessionId=${encodeURIComponent(sessionId)}`);
}

export function clearCart(sessionId) {
  return apiDelete(`/api/cart?sessionId=${encodeURIComponent(sessionId)}`);
}
