/**
 * Chat engine for the Bassets Help Center.
 *
 * Handles SSE streaming, message rendering, error recovery,
 * auto-scroll, stop generation, and rate limit handling.
 */

import { renderMarkdown, renderSources } from "./markdown.js";
import {
  getSessionId,
  setSessionId,
  touchSession,
  appendToHistory,
} from "./session.js";

// API base URL — same origin (help.bassets.net serves both page and API)
const API_BASE = window.location.origin;

// State
let isStreaming = false;
let abortController = null;

/**
 * Send a message and stream the response.
 * @param {string} text - User's question
 * @param {object} options
 * @param {Function} options.onChatMode - Called when entering chat mode
 * @param {Function} options.onComplete - Called when response is complete
 * @param {Function} options.onError - Called on error
 */
export async function sendMessage(text, { onChatMode, onComplete, onError }) {
  if (!text.trim() || isStreaming) return;

  isStreaming = true;
  abortController = new AbortController();

  const messagesEl = document.getElementById("chat-messages");
  if (!messagesEl) return;

  // Notify app to switch to chat mode
  if (onChatMode) onChatMode();

  // Render user message
  appendUserMessage(messagesEl, text);
  appendToHistory("user", text);
  touchSession();

  // Show typing indicator
  const typingEl = showTypingIndicator(messagesEl);
  scrollToBottom(messagesEl);

  // Disable send buttons
  setSendEnabled(false);

  // Show stop button
  const stopBtn = showStopButton(messagesEl);

  let fullAnswer = "";
  let sources = [];

  try {
    const sessionId = getSessionId();
    const response = await fetch(`${API_BASE}/chat/stream`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: text, session_id: sessionId }),
      signal: abortController.signal,
    });

    // Handle rate limiting
    if (response.status === 429) {
      removeElement(typingEl);
      removeElement(stopBtn);
      handleRateLimit(messagesEl, response);
      isStreaming = false;
      setSendEnabled(true);
      if (onError) onError("rate_limited");
      return;
    }

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    // Remove typing indicator, create assistant message bubble
    removeElement(typingEl);
    const { bubble: botBubble, wrapper: botWrapper } = appendAssistantMessage(messagesEl);

    // Process SSE stream
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop() || "";

      for (const line of lines) {
        if (!line.startsWith("data: ")) continue;

        try {
          const data = JSON.parse(line.slice(6));

          if (data.type === "session") {
            setSessionId(data.session_id);
          } else if (data.type === "sources") {
            sources = data.sources || [];
          } else if (data.type === "token") {
            fullAnswer += data.text;
            botBubble.innerHTML = renderMarkdown(fullAnswer);
            autoScroll(messagesEl);
          } else if (data.type === "error") {
            // Server-side error during streaming
            if (fullAnswer) {
              botBubble.innerHTML = renderMarkdown(fullAnswer);
            }
            appendRetryButton(botWrapper, text, { onChatMode, onComplete, onError });
          } else if (data.type === "done") {
            // Streaming complete
          }
        } catch {
          // Skip malformed SSE lines
        }
      }
    }

    // Finalize
    removeElement(stopBtn);
    botBubble.innerHTML = renderMarkdown(fullAnswer);

    // Add sources
    if (sources.length > 0) {
      botWrapper.insertAdjacentHTML("beforeend", renderSources(sources));
    }

    // Check if the bot couldn't answer — show contact card
    if (shouldShowContactCard(fullAnswer)) {
      botWrapper.insertAdjacentHTML("beforeend", renderContactCard());
    }

    appendToHistory("assistant", fullAnswer, sources);
    autoScroll(messagesEl);
    if (onComplete) onComplete();

  } catch (err) {
    removeElement(typingEl);
    removeElement(stopBtn);

    if (err.name === "AbortError") {
      // User stopped generation — keep partial response
      if (fullAnswer) {
        appendToHistory("assistant", fullAnswer, sources);
      }
      if (onComplete) onComplete();
    } else {
      // Network or other error — try fallback to /chat
      try {
        await sendFallback(messagesEl, text, { onComplete, onError });
      } catch {
        appendErrorMessage(messagesEl, text, { onChatMode, onComplete, onError });
        if (onError) onError("network_error");
      }
    }
  } finally {
    isStreaming = false;
    abortController = null;
    setSendEnabled(true);
    focusInput();
  }
}

/**
 * Stop the current streaming response.
 */
export function stopGeneration() {
  if (abortController) {
    abortController.abort();
  }
}

/**
 * Check if currently streaming.
 */
export function getIsStreaming() {
  return isStreaming;
}

/**
 * Restore cached messages from localStorage into the chat UI.
 * @param {Array} history - Array of {role, content, sources?} objects
 */
export function restoreMessages(history) {
  const messagesEl = document.getElementById("chat-messages");
  if (!messagesEl || !history.length) return;

  // Add a "Previous conversation" divider
  const divider = document.createElement("div");
  divider.className = "message__divider";
  divider.style.cssText =
    "text-align:center;font-size:12px;color:var(--color-text-muted);padding:var(--space-md) 0;opacity:0.7";
  divider.textContent = "Previous conversation";
  messagesEl.appendChild(divider);

  for (const msg of history) {
    if (msg.role === "user") {
      appendUserMessage(messagesEl, msg.content);
    } else if (msg.role === "assistant") {
      const { bubble, wrapper } = appendAssistantMessage(messagesEl);
      bubble.innerHTML = renderMarkdown(msg.content);
      if (msg.sources && msg.sources.length > 0) {
        wrapper.insertAdjacentHTML("beforeend", renderSources(msg.sources));
      }
    }
  }
}


// --- Internal Helpers ---

function appendUserMessage(container, text) {
  const wrapper = document.createElement("div");
  wrapper.className = "message message--user";
  const bubble = document.createElement("div");
  bubble.className = "message__bubble";
  bubble.textContent = text; // textContent for XSS safety
  wrapper.appendChild(bubble);
  container.appendChild(wrapper);
}

function appendAssistantMessage(container) {
  const wrapper = document.createElement("div");
  wrapper.className = "message message--assistant";
  const bubble = document.createElement("div");
  bubble.className = "message__bubble";
  wrapper.appendChild(bubble);
  container.appendChild(wrapper);
  return { bubble, wrapper };
}

function showTypingIndicator(container) {
  const el = document.createElement("div");
  el.className = "typing-indicator";
  el.setAttribute("aria-label", "Generating response");
  el.innerHTML = "<span></span><span></span><span></span>";
  container.appendChild(el);
  return el;
}

function showStopButton(container) {
  const btn = document.createElement("button");
  btn.className = "chat__stop-btn";
  btn.innerHTML = `
    <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><rect x="6" y="6" width="12" height="12" rx="1"/></svg>
    Stop generating
  `;
  btn.addEventListener("click", stopGeneration);
  container.appendChild(btn);
  return btn;
}

function appendRetryButton(container, originalText, callbacks) {
  const errorDiv = document.createElement("div");
  errorDiv.className = "message__error";
  errorDiv.innerHTML = `
    <span>Connection interrupted.</span>
    <button class="message__retry-btn">Retry</button>
  `;
  errorDiv.querySelector(".message__retry-btn").addEventListener("click", () => {
    removeElement(errorDiv);
    sendMessage(originalText, callbacks);
  });
  container.appendChild(errorDiv);
}

function appendErrorMessage(container, originalText, callbacks) {
  const wrapper = document.createElement("div");
  wrapper.className = "message message--assistant";
  wrapper.innerHTML = `
    <div class="message__bubble">
      I'm having trouble connecting right now. Please try again in a moment, or reach out to us directly.
    </div>
    <div class="message__error">
      <button class="message__retry-btn">Retry</button>
    </div>
  `;
  wrapper.querySelector(".message__retry-btn").addEventListener("click", () => {
    removeElement(wrapper);
    sendMessage(originalText, callbacks);
  });
  wrapper.insertAdjacentHTML("beforeend", renderContactCard());
  container.appendChild(wrapper);
}

function handleRateLimit(container, response) {
  const retryAfter = parseInt(response.headers.get("Retry-After") || "30", 10);

  const notice = document.createElement("div");
  notice.className = "chat__rate-limit";
  notice.innerHTML = `
    You're sending messages too quickly. Please wait <strong id="rate-countdown">${retryAfter}</strong> seconds.
  `;
  container.appendChild(notice);

  // Countdown
  let remaining = retryAfter;
  const countdownEl = notice.querySelector("#rate-countdown");
  const timer = setInterval(() => {
    remaining--;
    if (countdownEl) countdownEl.textContent = remaining;
    if (remaining <= 0) {
      clearInterval(timer);
      removeElement(notice);
    }
  }, 1000);

  autoScroll(container);
}

/**
 * Fallback to non-streaming /chat endpoint.
 */
async function sendFallback(container, text, { onComplete, onError }) {
  const sessionId = getSessionId();
  const response = await fetch(`${API_BASE}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message: text, session_id: sessionId }),
  });

  if (response.status === 429) {
    handleRateLimit(container, response);
    if (onError) onError("rate_limited");
    return;
  }

  if (!response.ok) throw new Error(`HTTP ${response.status}`);

  const data = await response.json();
  setSessionId(data.session_id);

  const { bubble, wrapper } = appendAssistantMessage(container);
  bubble.innerHTML = renderMarkdown(data.answer);

  if (data.sources && data.sources.length > 0) {
    wrapper.insertAdjacentHTML("beforeend", renderSources(data.sources));
  }

  if (shouldShowContactCard(data.answer)) {
    wrapper.insertAdjacentHTML("beforeend", renderContactCard());
  }

  appendToHistory("assistant", data.answer, data.sources);
  autoScroll(container);
  if (onComplete) onComplete();
}

function shouldShowContactCard(answer) {
  if (!answer) return false;
  const lower = answer.toLowerCase();
  return (
    lower.includes("contact") &&
    (lower.includes("support team") || lower.includes("sales team"))
  );
}

function renderContactCard() {
  return `
    <div class="contact-card">
      <div>
        <strong>Need more help?</strong><br>
        <a href="mailto:support@bassets.net">support@bassets.net</a> &middot;
        <a href="tel:+14759773237">(475) 977-3237</a>
      </div>
    </div>
  `;
}

function removeElement(el) {
  if (el && el.parentNode) {
    el.parentNode.removeChild(el);
  }
}

function setSendEnabled(enabled) {
  const heroBtn = document.getElementById("send-btn");
  const chatBtn = document.getElementById("chat-send-btn");
  if (heroBtn) heroBtn.disabled = !enabled;
  if (chatBtn) chatBtn.disabled = !enabled;
}

function focusInput() {
  const chatInput = document.getElementById("chat-input");
  const heroInput = document.getElementById("search-input");
  const target = chatInput && chatInput.offsetParent ? chatInput : heroInput;
  if (target) target.focus();
}

/**
 * Smart auto-scroll: only scroll if the user is near the bottom.
 */
function autoScroll(container) {
  const threshold = 150;
  const isNearBottom =
    container.scrollHeight - container.scrollTop - container.clientHeight < threshold;

  if (isNearBottom) {
    container.scrollTop = container.scrollHeight;
  } else {
    // Show "scroll to bottom" button
    const scrollBtn = document.getElementById("scroll-btn");
    if (scrollBtn) scrollBtn.hidden = false;
  }
}

/**
 * Force scroll to bottom (used by scroll-btn click).
 */
export function scrollToBottom(container) {
  if (container) {
    container.scrollTop = container.scrollHeight;
  }
  const scrollBtn = document.getElementById("scroll-btn");
  if (scrollBtn) scrollBtn.hidden = true;
}
