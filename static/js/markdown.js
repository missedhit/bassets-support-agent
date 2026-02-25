/**
 * Markdown renderer for the Bassets Help Center.
 *
 * Converts a subset of Markdown to HTML, optimized for chat messages.
 * XSS-safe: escapes HTML entities BEFORE processing Markdown tokens.
 *
 * Supported syntax:
 *   **bold**, *italic*, `inline code`, ```code blocks```,
 *   ordered lists, unordered lists, paragraphs, [links](url)
 */

/**
 * Escape HTML entities to prevent XSS.
 */
function escapeHtml(text) {
  return text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

/**
 * Render Markdown text to safe HTML.
 * @param {string} text - Raw Markdown text
 * @returns {string} - HTML string
 */
export function renderMarkdown(text) {
  if (!text) return "";

  // Escape HTML first (XSS prevention)
  let html = escapeHtml(text);

  // Code blocks (```)
  html = html.replace(/```(\w*)\n?([\s\S]*?)```/g, (_match, _lang, code) => {
    return `<pre><code>${code.trim()}</code></pre>`;
  });

  // Inline code
  html = html.replace(/`([^`\n]+)`/g, "<code>$1</code>");

  // Bold
  html = html.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");

  // Italic (single asterisk, but not inside words)
  html = html.replace(/(?<!\w)\*([^*\n]+)\*(?!\w)/g, "<em>$1</em>");

  // Links: [text](url)
  html = html.replace(
    /\[([^\]]+)\]\(([^)]+)\)/g,
    '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>'
  );

  // Process blocks (split on double newlines)
  const blocks = html.split(/\n\n+/);
  const rendered = [];

  for (let block of blocks) {
    block = block.trim();
    if (!block) continue;

    // Numbered list
    if (/^\d+\.\s/.test(block)) {
      const items = block.split(/\n/).map((line) =>
        line.replace(/^\d+\.\s+/, "")
      );
      rendered.push(
        "<ol>" + items.map((item) => `<li>${item}</li>`).join("") + "</ol>"
      );
      continue;
    }

    // Bullet list
    if (/^[-*]\s/.test(block)) {
      const items = block.split(/\n/).map((line) =>
        line.replace(/^[-*]\s+/, "")
      );
      rendered.push(
        "<ul>" + items.map((item) => `<li>${item}</li>`).join("") + "</ul>"
      );
      continue;
    }

    // Pre blocks already handled (pass through)
    if (block.startsWith("<pre>")) {
      rendered.push(block);
      continue;
    }

    // Regular paragraph — convert single newlines to <br>
    block = block.replace(/\n/g, "<br>");
    rendered.push(`<p>${block}</p>`);
  }

  return rendered.join("");
}

/**
 * Render source citations as HTML.
 * @param {Array} sources - Array of source objects from the API
 * @returns {string} - HTML string for the sources section
 */
export function renderSources(sources) {
  if (!sources || sources.length === 0) return "";

  const pills = sources
    .map((s) => {
      const label = s.section
        ? `${s.file} — ${s.section}`
        : s.file || s.type || "Source";
      return `<span class="source-pill">${escapeHtml(label)}</span>`;
    })
    .join("");

  return `
    <div class="message__sources">
      <button class="message__sources-toggle" aria-expanded="false" onclick="this.setAttribute('aria-expanded', this.getAttribute('aria-expanded') === 'true' ? 'false' : 'true'); this.nextElementSibling.classList.toggle('open')">
        <svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor"><path d="M7.41 8.59L12 13.17l4.59-4.58L18 10l-6 6-6-6z"/></svg>
        ${sources.length} source${sources.length === 1 ? "" : "s"}
      </button>
      <div class="message__sources-list">${pills}</div>
    </div>
  `;
}
