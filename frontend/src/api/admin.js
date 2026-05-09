import { apiDelete, apiPost, apiPut } from "./client";

export function createProduct(product) {
  return apiPost("/api/admin/products", product);
}

export function updateProduct(id, product) {
  return apiPut(`/api/admin/products/${id}`, product);
}

export function deleteProduct(id) {
  return apiDelete(`/api/admin/products/${id}`);
}
