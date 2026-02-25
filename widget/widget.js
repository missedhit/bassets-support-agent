/**
 * Bassets Support Agent - Embeddable Chat Widget
 *
 * Drop this single script tag on any page of bassets.net:
 *
 *   <script src="https://your-server.com/widget.js" data-api="https://your-server.com"></script>
 *
 * That is it. The widget renders itself.
 */

(function () {
  "use strict";

  // --- Config ---
  const SCRIPT_TAG = document.currentScript;
  const API_BASE = SCRIPT_TAG?.getAttribute("data-api") || "http://localhost:8000";
  const BRAND_COLOR = SCRIPT_TAG?.getAttribute("data-color") || "#1A5276";
  const POSITION = SCRIPT_TAG?.getAttribute("data-position") || "right"; // "left" or "right"
  const GREETING = SCRIPT_TAG?.getAttribute("data-greeting") ||
    "Hi! I'm the Bassets support assistant. Ask me anything about fixed asset management, depreciation, or how to use the software.";

  let sessionId = null;
  let isOpen = false;
  let isLoading = false;

  // --- Styles ---
  const STYLES = `
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600&display=swap');

    #bassets-chat-widget * {
      box-sizing: border-box;
      margin: 0;
      padding: 0;
      font-family: 'DM Sans', -apple-system, BlinkMacSystemFont, sans-serif;
    }

    #bassets-chat-bubble {
      position: fixed;
      bottom: 24px;
      ${POSITION}: 24px;
      width: 60px;
      height: 60px;
      border-radius: 50%;
      background: ${BRAND_COLOR};
      color: white;
      border: none;
      cursor: pointer;
      box-shadow: 0 4px 20px rgba(0,0,0,0.2);
      display: flex;
      align-items: center;
      justify-content: center;
      z-index: 99998;
      transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    #bassets-chat-bubble:hover {
      transform: scale(1.08);
      box-shadow: 0 6px 28px rgba(0,0,0,0.28);
    }
    #bassets-chat-bubble svg {
      width: 28px;
      height: 28px;
      fill: white;
    }

    #bassets-chat-window {
      position: fixed;
      bottom: 100px;
      ${POSITION}: 24px;
      width: 400px;
      max-width: calc(100vw - 32px);
      height: 560px;
      max-height: calc(100vh - 140px);
      border-radius: 16px;
      background: #fff;
      box-shadow: 0 12px 48px rgba(0,0,0,0.18);
      display: none;
      flex-direction: column;
      overflow: hidden;
      z-index: 99999;
      animation: bassets-slide-up 0.25s ease-out;
    }
    #bassets-chat-window.open { display: flex; }

    @keyframes bassets-slide-up {
      from { opacity: 0; transform: translateY(16px); }
      to { opacity: 1; transform: translateY(0); }
    }

    /* Header */
    .bassets-header {
      background: ${BRAND_COLOR};
      color: white;
      padding: 18px 20px;
      display: flex;
      align-items: center;
      gap: 12px;
      flex-shrink: 0;
    }
    .bassets-header-icon {
      width: 36px;
      height: 36px;
      background: rgba(255,255,255,0.18);
      border-radius: 10px;
      display: flex;
      align-items: center;
      justify-content: center;
      flex-shrink: 0;
    }
    .bassets-header-icon svg { width: 20px; height: 20px; fill: white; }
    .bassets-header-text h3 {
      font-size: 15px;
      font-weight: 600;
      letter-spacing: -0.01em;
    }
    .bassets-header-text p {
      font-size: 12px;
      opacity: 0.8;
      margin-top: 2px;
    }
    .bassets-close-btn {
      margin-left: auto;
      background: rgba(255,255,255,0.15);
      border: none;
      color: white;
      width: 30px;
      height: 30px;
      border-radius: 8px;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 18px;
      transition: background 0.15s;
    }
    .bassets-close-btn:hover { background: rgba(255,255,255,0.28); }

    /* Messages area */
    .bassets-messages {
      flex: 1;
      overflow-y: auto;
      padding: 16px;
      display: flex;
      flex-direction: column;
      gap: 12px;
      background: #F9FAFB;
    }
    .bassets-messages::-webkit-scrollbar { width: 5px; }
    .bassets-messages::-webkit-scrollbar-thumb {
      background: #D1D5DB;
      border-radius: 10px;
    }

    .bassets-msg {
      max-width: 85%;
      padding: 12px 16px;
      border-radius: 14px;
      font-size: 14px;
      line-height: 1.55;
      word-wrap: break-word;
    }
    .bassets-msg.bot {
      background: white;
      color: #1F2937;
      align-self: flex-start;
      border: 1px solid #E5E7EB;
      border-bottom-left-radius: 4px;
    }
    .bassets-msg.user {
      background: ${BRAND_COLOR};
      color: white;
      align-self: flex-end;
      border-bottom-right-radius: 4px;
    }
    .bassets-msg.bot strong { font-weight: 600; }
    .bassets-msg.bot ol, .bassets-msg.bot ul {
      margin: 6px 0 6px 20px;
    }
    .bassets-msg.bot li { margin-bottom: 4px; }
    .bassets-msg.bot p { margin-bottom: 8px; }
    .bassets-msg.bot p:last-child { margin-bottom: 0; }
    .bassets-msg.bot code {
      background: #F3F4F6;
      padding: 1px 5px;
      border-radius: 4px;
      font-size: 13px;
    }

    /* Typing indicator */
    .bassets-typing {
      display: flex;
      gap: 5px;
      padding: 12px 16px;
      align-self: flex-start;
    }
    .bassets-typing span {
      width: 8px;
      height: 8px;
      background: #CBD5E1;
      border-radius: 50%;
      animation: bassets-bounce 1.2s infinite;
    }
    .bassets-typing span:nth-child(2) { animation-delay: 0.15s; }
    .bassets-typing span:nth-child(3) { animation-delay: 0.3s; }
    @keyframes bassets-bounce {
      0%, 60%, 100% { transform: translateY(0); }
      30% { transform: translateY(-6px); }
    }

    /* Input area */
    .bassets-input-area {
      padding: 12px 16px;
      border-top: 1px solid #E5E7EB;
      display: flex;
      gap: 8px;
      align-items: center;
      background: white;
      flex-shrink: 0;
    }
    .bassets-input-area input {
      flex: 1;
      border: 1px solid #E5E7EB;
      border-radius: 10px;
      padding: 10px 14px;
      font-size: 14px;
      font-family: inherit;
      outline: none;
      transition: border-color 0.15s;
    }
    .bassets-input-area input:focus { border-color: ${BRAND_COLOR}; }
    .bassets-input-area input::placeholder { color: #9CA3AF; }

    .bassets-send-btn {
      width: 40px;
      height: 40px;
      border-radius: 10px;
      background: ${BRAND_COLOR};
      border: none;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      transition: opacity 0.15s;
      flex-shrink: 0;
    }
    .bassets-send-btn:disabled { opacity: 0.4; cursor: not-allowed; }
    .bassets-send-btn svg { width: 18px; height: 18px; fill: white; }

    .bassets-powered {
      text-align: center;
      padding: 6px;
      font-size: 11px;
      color: #9CA3AF;
      background: white;
      flex-shrink: 0;
    }

    /* Mobile */
    @media (max-width: 480px) {
      #bassets-chat-window {
        width: 100vw;
        height: 100vh;
        max-height: 100vh;
        bottom: 0;
        ${POSITION}: 0;
        border-radius: 0;
      }
      #bassets-chat-bubble { bottom: 16px; ${POSITION}: 16px; }
    }
  `;

  // --- Build DOM ---
  function createWidget() {
    // Style tag
    const style = document.createElement("style");
    style.textContent = STYLES;
    document.head.appendChild(style);

    // Container
    const container = document.createElement("div");
    container.id = "bassets-chat-widget";
    container.innerHTML = `
      <button id="bassets-chat-bubble" aria-label="Open support chat">
        <svg viewBox="0 0 24 24"><path d="M20 2H4c-1.1 0-2 .9-2 2v18l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zm0 14H6l-2 2V4h16v12z"/></svg>
      </button>

      <div id="bassets-chat-window">
        <div class="bassets-header">
          <div class="bassets-header-icon">
            <svg viewBox="0 0 24 24"><path d="M20 2H4c-1.1 0-2 .9-2 2v18l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zm0 14H6l-2 2V4h16v12z"/></svg>
          </div>
          <div class="bassets-header-text">
            <h3>Bassets Support</h3>
            <p>AI-powered help for fixed asset management</p>
          </div>
          <button class="bassets-close-btn" aria-label="Close chat">&times;</button>
        </div>

        <div class="bassets-messages" id="bassets-messages">
          <div class="bassets-msg bot">${GREETING}</div>
        </div>

        <div class="bassets-input-area">
          <input type="text" id="bassets-input" placeholder="Ask a question..." autocomplete="off" />
          <button class="bassets-send-btn" id="bassets-send" aria-label="Send message">
            <svg viewBox="0 0 24 24"><path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/></svg>
          </button>
        </div>

        <div class="bassets-powered">Powered by Bassets AI</div>
      </div>
    `;
    document.body.appendChild(container);

    // Wire up events
    const bubble = document.getElementById("bassets-chat-bubble");
    const chatWindow = document.getElementById("bassets-chat-window");
    const closeBtn = container.querySelector(".bassets-close-btn");
    const input = document.getElementById("bassets-input");
    const sendBtn = document.getElementById("bassets-send");

    bubble.addEventListener("click", () => toggleChat(chatWindow, bubble));
    closeBtn.addEventListener("click", () => toggleChat(chatWindow, bubble));
    sendBtn.addEventListener("click", () => sendMessage(input));
    input.addEventListener("keydown", (e) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        sendMessage(input);
      }
    });
  }

  function toggleChat(chatWindow, bubble) {
    isOpen = !isOpen;
    chatWindow.classList.toggle("open", isOpen);
    bubble.style.display = isOpen ? "none" : "flex";
    if (isOpen) {
      setTimeout(() => document.getElementById("bassets-input")?.focus(), 100);
    }
  }

  // --- Chat Logic ---
  function addMessage(text, sender) {
    const messages = document.getElementById("bassets-messages");
    const msg = document.createElement("div");
    msg.className = `bassets-msg ${sender}`;

    if (sender === "bot") {
      msg.innerHTML = formatMarkdown(text);
    } else {
      msg.textContent = text;
    }

    messages.appendChild(msg);
    messages.scrollTop = messages.scrollHeight;
    return msg;
  }

  function showTyping() {
    const messages = document.getElementById("bassets-messages");
    const typing = document.createElement("div");
    typing.className = "bassets-typing";
    typing.id = "bassets-typing";
    typing.innerHTML = "<span></span><span></span><span></span>";
    messages.appendChild(typing);
    messages.scrollTop = messages.scrollHeight;
  }

  function hideTyping() {
    document.getElementById("bassets-typing")?.remove();
  }

  function formatMarkdown(text) {
    // Basic markdown formatting for bot responses
    let html = text
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");

    // Bold
    html = html.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");

    // Inline code
    html = html.replace(/`([^`]+)`/g, "<code>$1</code>");

    // Numbered lists
    html = html.replace(/^(\d+)\.\s+(.+)$/gm, "<li>$2</li>");
    html = html.replace(/(<li>.*<\/li>\n?)+/g, (match) => `<ol>${match}</ol>`);

    // Bullet lists
    html = html.replace(/^[-*]\s+(.+)$/gm, "<li>$1</li>");
    html = html.replace(/(<li>.*<\/li>\n?)+/g, (match) => {
      if (match.includes("<ol>")) return match;
      return `<ul>${match}</ul>`;
    });

    // Paragraphs (double newlines)
    html = html.replace(/\n\n/g, "</p><p>");
    html = `<p>${html}</p>`;
    html = html.replace(/<p>\s*<\/p>/g, "");

    return html;
  }

  async function sendMessage(input) {
    const text = input.value.trim();
    if (!text || isLoading) return;

    input.value = "";
    isLoading = true;
    document.getElementById("bassets-send").disabled = true;

    addMessage(text, "user");
    showTyping();

    try {
      // Try streaming first
      const response = await fetch(`${API_BASE}/chat/stream`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: text, session_id: sessionId }),
      });

      if (!response.ok) throw new Error(`HTTP ${response.status}`);

      hideTyping();
      const botMsg = addMessage("", "bot");
      let fullText = "";

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
              sessionId = data.session_id;
            } else if (data.type === "token") {
              fullText += data.text;
              botMsg.innerHTML = formatMarkdown(fullText);
              document.getElementById("bassets-messages").scrollTop =
                document.getElementById("bassets-messages").scrollHeight;
            }
          } catch (e) {
            // Skip malformed SSE lines
          }
        }
      }

    } catch (err) {
      // Fallback to non-streaming endpoint
      try {
        const response = await fetch(`${API_BASE}/chat`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ message: text, session_id: sessionId }),
        });

        const data = await response.json();
        hideTyping();
        sessionId = data.session_id;
        addMessage(data.answer, "bot");

      } catch (fallbackErr) {
        hideTyping();
        addMessage(
          "Sorry, I am having trouble connecting right now. Please try again in a moment, or contact support directly at bassets.net.",
          "bot"
        );
      }
    }

    isLoading = false;
    document.getElementById("bassets-send").disabled = false;
    document.getElementById("bassets-input")?.focus();
  }

  // --- Initialize ---
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", createWidget);
  } else {
    createWidget();
  }
})();
