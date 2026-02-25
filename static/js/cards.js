/**
 * Common query cards for the Bassets Help Center.
 *
 * Each card represents a popular support topic. Clicking a card
 * fills the search input with a sample question and auto-submits it.
 */

// Card data — based on real Bassets product areas and support ticket topics
const CARDS = [
  {
    id: "depreciation",
    title: "Depreciation Methods",
    desc: "Learn about MACRS, Straight-Line, Declining Balance, and other methods",
    question: "How do I set up MACRS depreciation in Bassets?",
    icon: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
      <rect x="4" y="2" width="16" height="20" rx="2"/>
      <line x1="8" y1="6" x2="16" y2="6"/>
      <line x1="8" y1="10" x2="16" y2="10"/>
      <line x1="8" y1="14" x2="12" y2="14"/>
      <line x1="8" y1="18" x2="10" y2="18"/>
    </svg>`,
  },
  {
    id: "installation",
    title: "Installation & Setup",
    desc: "Installing, configuring, and upgrading Bassets eDepreciation",
    question: "What are the system requirements for installing Bassets eDepreciation?",
    icon: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
      <circle cx="12" cy="12" r="3"/>
      <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/>
    </svg>`,
  },
  {
    id: "reports",
    title: "Reports & Schedules",
    desc: "Generate depreciation schedules, asset registers, and custom reports",
    question: "How do I generate a depreciation schedule report?",
    icon: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
      <polyline points="14 2 14 8 20 8"/>
      <line x1="16" y1="13" x2="8" y2="13"/>
      <line x1="16" y1="17" x2="8" y2="17"/>
      <polyline points="10 9 9 9 8 9"/>
    </svg>`,
  },
  {
    id: "asset-management",
    title: "Asset Management",
    desc: "Adding, editing, disposing, and transferring fixed assets",
    question: "How do I record an asset disposal in Bassets?",
    icon: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
      <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>
      <polyline points="9 22 9 12 15 12 15 22"/>
    </svg>`,
  },
  {
    id: "import-export",
    title: "Data Import & Export",
    desc: "Import assets from CSV/Excel or export your data",
    question: "How do I import assets from an Excel spreadsheet?",
    icon: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
      <polyline points="16 16 12 12 8 16"/>
      <line x1="12" y1="12" x2="12" y2="21"/>
      <path d="M20.39 18.39A5 5 0 0 0 18 9h-1.26A8 8 0 1 0 3 16.3"/>
    </svg>`,
  },
  {
    id: "section179",
    title: "Section 179 & Bonus",
    desc: "Special deductions, Section 179 elections, and bonus depreciation",
    question: "How do I apply Section 179 deduction to an asset?",
    icon: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
      <line x1="12" y1="1" x2="12" y2="23"/>
      <path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/>
    </svg>`,
  },
  {
    id: "login",
    title: "Login & Licensing",
    desc: "Password resets, license activation, and access troubleshooting",
    question: "My login credentials are not working after an update. How do I fix this?",
    icon: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
      <rect x="3" y="11" width="18" height="11" rx="2" ry="2"/>
      <path d="M7 11V7a5 5 0 0 1 10 0v4"/>
      <circle cx="12" cy="16" r="1"/>
    </svg>`,
  },
  {
    id: "cloud",
    title: "Cloud & Server Setup",
    desc: "Cloud edition setup, server migration, and database configuration",
    question: "How do I migrate Bassets to a new server?",
    icon: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
      <path d="M18 10h-1.26A8 8 0 1 0 9 20h9a5 5 0 0 0 0-10z"/>
    </svg>`,
  },
];

/**
 * Render cards into the grid container.
 * @param {Function} onCardClick - Callback invoked with the card's sample question
 */
export function renderCards(onCardClick) {
  const grid = document.getElementById("cards-grid");
  if (!grid) return;

  grid.innerHTML = "";

  for (const card of CARDS) {
    const el = document.createElement("article");
    el.className = "card";
    el.role = "listitem";
    el.tabIndex = 0;
    el.setAttribute("aria-label", `${card.title}: ${card.desc}`);
    el.dataset.question = card.question;

    el.innerHTML = `
      <div class="card__icon" aria-hidden="true">${card.icon}</div>
      <div class="card__content">
        <div class="card__title">${card.title}</div>
        <div class="card__desc">${card.desc}</div>
      </div>
    `;

    // Click and keyboard handlers
    const handleSelect = () => onCardClick(card.question);
    el.addEventListener("click", handleSelect);
    el.addEventListener("keydown", (e) => {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        handleSelect();
      }
    });

    grid.appendChild(el);
  }
}

export { CARDS };
