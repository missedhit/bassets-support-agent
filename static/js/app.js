/**
 * Bassets Help Center — Main Application Controller
 *
 * Initializes all modules, manages browse/chat state transitions,
 * and coordinates the overall UX flow.
 */

import { renderCards } from "./cards.js";
import {
  sendMessage,
  stopGeneration,
  getIsStreaming,
  restoreMessages,
  scrollToBottom,
} from "./chat.js";
import {
  getSessionId,
  hasValidSession,
  isSessionExpired,
  clearSession,
  clearHistory,
  getHistory,
} from "./session.js";

// --- State ---
let chatMode = false;

// --- DOM Elements ---
let heroInput;
let chatInput;
let searchForm;
let chatForm;
let chatSection;
let messagesEl;
let scrollBtn;
let newChatBtn;

// --- Initialize ---
document.addEventListener("DOMContentLoaded", () => {
  // Cache DOM elements
  heroInput = document.getElementById("search-input");
  chatInput = document.getElementById("chat-input");
  searchForm = document.getElementById("search-form");
  chatForm = document.getElementById("chat-form");
  chatSection = document.getElementById("chat-section");
  messagesEl = document.getElementById("chat-messages");
  scrollBtn = document.getElementById("scroll-btn");
  newChatBtn = document.getElementById("new-chat-btn");

  // Render cards
  renderCards(handleCardClick);

  // Form submissions
  searchForm.addEventListener("submit", handleHeroSubmit);
  chatForm.addEventListener("submit", handleChatSubmit);

  // New conversation button
  newChatBtn.addEventListener("click", handleNewConversation);

  // Scroll-to-bottom button
  scrollBtn.addEventListener("click", () => {
    scrollToBottom(messagesEl);
  });

  // Track scroll position to show/hide scroll-btn
  messagesEl.addEventListener("scroll", () => {
    const threshold = 150;
    const isNearBottom =
      messagesEl.scrollHeight - messagesEl.scrollTop - messagesEl.clientHeight <
      threshold;
    scrollBtn.hidden = isNearBottom;
  });

  // Character count on inputs
  setupCharCount(heroInput, "char-count");
  setupCharCount(chatInput, "chat-char-count");

  // Restore previous session if valid
  restoreSession();

  // Announce to screen readers
  announce("Bassets Help Center loaded. Type your question to get started.");
});

// --- Event Handlers ---

function handleHeroSubmit(e) {
  e.preventDefault();
  const text = heroInput.value.trim();
  if (!text) return;

  heroInput.value = "";
  hideCharCount("char-count");

  submitQuestion(text);
}

function handleChatSubmit(e) {
  e.preventDefault();
  const text = chatInput.value.trim();
  if (!text || getIsStreaming()) return;

  chatInput.value = "";
  hideCharCount("chat-char-count");

  submitQuestion(text);
}

function handleCardClick(question) {
  submitQuestion(question);
}

function submitQuestion(text) {
  sendMessage(text, {
    onChatMode: enterChatMode,
    onComplete: () => {
      announce("Response received.");
    },
    onError: (type) => {
      if (type === "rate_limited") {
        announce("Rate limit reached. Please wait before sending another message.");
      } else {
        announce("An error occurred. You can retry your question.");
      }
    },
  });
}

function handleNewConversation() {
  // Clear state
  clearSession();
  clearHistory();

  // Clear UI
  messagesEl.innerHTML = "";

  // Return to browse mode
  exitChatMode();

  // Focus the hero input
  heroInput.focus();

  announce("New conversation started.");
}


// --- State Transitions ---

function enterChatMode() {
  if (chatMode) return;
  chatMode = true;

  document.body.classList.add("chat-mode");
  chatSection.hidden = false;

  // Focus the chat input after transition
  setTimeout(() => {
    chatInput.focus();
  }, 100);
}

function exitChatMode() {
  chatMode = false;
  document.body.classList.remove("chat-mode");
  chatSection.hidden = true;
}


// --- Session Restoration ---

function restoreSession() {
  // Check if there's an expired session
  if (isSessionExpired()) {
    clearSession();
    clearHistory();
    return;
  }

  // If there's a valid session with history, restore it
  if (hasValidSession()) {
    const history = getHistory();
    if (history.length > 0) {
      enterChatMode();
      restoreMessages(history);
      scrollToBottom(messagesEl);
    }
  }
}


// --- Character Count ---

function setupCharCount(input, countElId) {
  if (!input) return;
  const maxLen = parseInt(input.getAttribute("maxlength") || "2000", 10);

  input.addEventListener("input", () => {
    const len = input.value.length;
    const countEl = document.getElementById(countElId);
    if (!countEl) return;

    if (len > maxLen * 0.8) {
      countEl.hidden = false;
      countEl.textContent = `${len} / ${maxLen}`;
      countEl.className = countEl.className.replace(/warning|error/g, "").trim();

      if (len > maxLen * 0.95) {
        countEl.classList.add("error");
      } else {
        countEl.classList.add("warning");
      }
    } else {
      countEl.hidden = true;
    }
  });
}

function hideCharCount(countElId) {
  const countEl = document.getElementById(countElId);
  if (countEl) countEl.hidden = true;
}


// --- Accessibility ---

/**
 * Announce a message to screen readers via the live region.
 */
function announce(message) {
  const el = document.getElementById("sr-announcements");
  if (el) {
    el.textContent = message;
    // Clear after a delay so repeated identical messages still announce
    setTimeout(() => {
      el.textContent = "";
    }, 1000);
  }
}


// --- Keyboard Shortcuts ---

document.addEventListener("keydown", (e) => {
  // Escape: stop streaming or return to browse mode
  if (e.key === "Escape") {
    if (getIsStreaming()) {
      stopGeneration();
    }
  }
});
