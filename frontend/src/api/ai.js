import { apiPost } from "./client";
import { getSessionId } from "../utils/session";

export function requestRecommendation(message, sessionId) {
  return apiPost("/api/ai/recommend", { message, session_id: sessionId || getSessionId() });
}

export function requestAiCompare(productIds, criteria) {
  return apiPost("/api/ai/compare", { product_ids: productIds, criteria });
}

export function requestReviewSummary(productId) {
  return apiPost("/api/ai/review-summary", { product_id: productId });
}
