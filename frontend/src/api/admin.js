import { apiDelete, apiGet, apiPost, apiPut } from "./client";

export function fetchAiSettings() {
  return apiGet("/api/admin/ai-settings");
}

export function updateAiSettings(settings) {
  return apiPut("/api/admin/ai-settings", settings);
}

export function fetchAiModels(provider, baseUrl, apiKey = "") {
  return apiGet("/api/admin/ai-settings/models", {
    provider,
    base_url: baseUrl,
    api_key: apiKey,
  });
}

export function testAiSettings(settings) {
  return apiPost("/api/admin/ai-settings/test", settings);
}

export function unloadAiModel(provider, model = "") {
  return apiPost("/api/admin/ai-settings/unload", { provider, model });
}

export function createProduct(product) {
  return apiPost("/api/admin/products", product);
}

export function updateProduct(id, product) {
  return apiPut(`/api/admin/products/${id}`, product);
}

export function deleteProduct(id) {
  return apiDelete(`/api/admin/products/${id}`);
}
