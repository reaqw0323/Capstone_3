import { apiGet } from "./client";

export function fetchCategories() {
  return apiGet("/api/categories");
}

export function fetchProducts(filters = {}) {
  return apiGet("/api/products", filters);
}

export function fetchProduct(id) {
  return apiGet(`/api/products/${id}`);
}

export function fetchProductReviews(id) {
  return apiGet(`/api/products/${id}/reviews`);
}

export function fetchCompareProducts(ids) {
  return apiGet("/api/products/compare", { ids: ids.join(",") });
}
