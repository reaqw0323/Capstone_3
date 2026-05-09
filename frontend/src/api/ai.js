import { apiPost } from "./client";

export function requestRecommendation(message) {
  return apiPost("/api/ai/recommend", { message });
}

export function requestAiCompare(productIds, criteria) {
  return apiPost("/api/ai/compare", { product_ids: productIds, criteria });
}

export function requestReviewSummary(productId) {
  return apiPost("/api/ai/review-summary", { product_id: productId });
}
