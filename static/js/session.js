/**
 * Session management for the Bassets Help Center.
 *
 * Manages the server-side session ID and provides localStorage backup
 * for conversation continuity across page refreshes.
 */

const STORAGE_KEY = "bassets_help_session";
const HISTORY_KEY = "bassets_help_history";
const SESSION_TTL_MS = 2 * 60 * 60 * 1000; // 2 hours (matches server TTL)
const MAX_HISTORY = 20; // Max messages to store locally

/**
 * Get the current session ID (from memory or localStorage).
 * Returns null if no valid session exists.
 */
export function getSessionId() {
  try {
    const data = JSON.parse(localStorage.getItem(STORAGE_KEY));
    if (!data || !data.sessionId) return null;

    // Check if session has expired
    if (Date.now() - data.lastActive > SESSION_TTL_MS) {
      clearSession();
      return null;
    }

    return data.sessionId;
  } catch {
    return null;
  }
}

/**
 * Save or update the session ID.
 */
export function setSessionId(sessionId) {
  try {
    localStorage.setItem(
      STORAGE_KEY,
      JSON.stringify({
        sessionId,
        lastActive: Date.now(),
      })
    );
  } catch {
    // localStorage unavailable — proceed without persistence
  }
}

/**
 * Mark the session as active (update timestamp).
 */
export function touchSession() {
  try {
    const data = JSON.parse(localStorage.getItem(STORAGE_KEY));
    if (data) {
      data.lastActive = Date.now();
      localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
    }
  } catch {
    // Ignore
  }
}

/**
 * Clear the session entirely.
 */
export function clearSession() {
  try {
    localStorage.removeItem(STORAGE_KEY);
    localStorage.removeItem(HISTORY_KEY);
  } catch {
    // Ignore
  }
}

/**
 * Check if a previous session exists and is still valid.
 */
export function hasValidSession() {
  return getSessionId() !== null;
}

/**
 * Check if the session has expired (had one, but it's too old).
 */
export function isSessionExpired() {
  try {
    const data = JSON.parse(localStorage.getItem(STORAGE_KEY));
    if (!data || !data.sessionId) return false;
    return Date.now() - data.lastActive > SESSION_TTL_MS;
  } catch {
    return false;
  }
}


// --- Conversation History (localStorage backup) ---

/**
 * Get stored conversation history.
 * @returns {Array} Array of {role, content, sources?, timestamp} objects
 */
export function getHistory() {
  try {
    const data = JSON.parse(localStorage.getItem(HISTORY_KEY));
    return Array.isArray(data) ? data : [];
  } catch {
    return [];
  }
}

/**
 * Append a message to the stored conversation history.
 * @param {string} role - "user" or "assistant"
 * @param {string} content - Message text
 * @param {Array} [sources] - Source citations (for assistant messages)
 */
export function appendToHistory(role, content, sources = null) {
  try {
    const history = getHistory();
    const entry = { role, content, timestamp: Date.now() };
    if (sources && sources.length > 0) {
      entry.sources = sources;
    }
    history.push(entry);

    // Keep only the last MAX_HISTORY messages
    const trimmed = history.slice(-MAX_HISTORY);
    localStorage.setItem(HISTORY_KEY, JSON.stringify(trimmed));
  } catch {
    // Ignore
  }
}

/**
 * Clear conversation history.
 */
export function clearHistory() {
  try {
    localStorage.removeItem(HISTORY_KEY);
  } catch {
    // Ignore
  }
}
