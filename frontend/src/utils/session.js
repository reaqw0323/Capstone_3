const SESSION_KEY = "easypick_session_id";

export function getSessionId() {
  const saved = localStorage.getItem(SESSION_KEY);
  if (saved) return saved;

  const next =
    window.crypto?.randomUUID?.() ||
    `session-${Date.now()}-${Math.random().toString(16).slice(2)}`;
  localStorage.setItem(SESSION_KEY, next);
  return next;
}
