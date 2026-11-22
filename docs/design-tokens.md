# Careem MCP Meal Planner — Design System & Design Tokens

This document defines the official visual design tokens, typography scale, accessibility rules, and surface styling for the Careem MCP Meal Planner hackathon project. It blends Careem's super-app visual identity with a high-tech, futuristic aesthetic while strictly enforcing WCAG AA/AAA contrast standards.

---

## 1. Color Palette Matrix

Careem's signature green (`#00EB79` / `#008744`) provides energetic accents. To ensure maximum legibility, the color system uses explicit pairs for light and dark surfaces.

### Dark Mode (Default / Futuristic Glow)
| Token | Hex Value | Role / Application |
|---|---|---|
| `--bg-base` | `#070B09` | Main canvas background (Obsidian with 2% green tint) |
| `--bg-surface` | `#0F1613` | Recipe cards, pantry rows, checkout drawers |
| `--bg-elevated` | `#16211C` | Hover states, active inputs, 3D card highlights |
| `--border-subtle` | `#22322A` | Subdued borders & dividers |
| `--text-primary` | `#F3F7F5` | Main titles, recipe names, primary prices |
| `--text-secondary` | `#9FB3A8` | Subtitles, prep times, calorie counts |
| `--brand-primary` | `#00EB79` | Careem Electric Green (CTAs, active tabs, buttons) |
| `--brand-hover` | `#2BFF96` | Hover state for Careem Green CTAs |
| `--brand-on-primary` | `#041E10` | Dark text/icons placed **inside** `#00EB79` buttons |

### Light Mode (Classic Careem Quik)
| Token | Hex Value | Role / Application |
|---|---|---|
| `--bg-base` | `#F4F7F5` | Light canvas background |
| `--bg-surface` | `#FFFFFF` | Meal cards, ingredient list, modal dialogs |
| `--bg-elevated` | `#E9F2ED` | Selected chips, hover states, badges |
| `--border-subtle` | `#D1DFD7` | Light mode card borders |
| `--text-primary` | `#0D1B14` | Main headings, dish titles |
| `--text-secondary` | `#465B50` | Secondary metadata and labels |
| `--brand-primary` | `#008744` | Core Careem Green (Buttons, active states) |
| `--brand-hover` | `#007038` | Button hover state |
| `--brand-on-primary` | `#FFFFFF` | White text inside `#008744` buttons |

### Functional & Semantic Accents
| Token | Dark Mode Hex | Light Mode Hex | Usage |
|---|---|---|---|
| `--deal-bg` / `--deal-text` | `#2E2105` / `#FFC233` | `#FFF4D6` / `#8A5300` | Careem Quik live promo & deal badges |
| `--pantry-have` | `#00EB79` | `#008744` | "In Pantry" checks & diff indicator |
| `--allergen-bg` / `--allergen-text` | `#331014` / `#FF6B72` | `#FDECEC` / `#B42318` | Allergen warnings & blocked ingredients |
| `--ai-accent` | `#38BDF8` | `#026AA2` | AI magic prompt, smart swap highlights |

---

## 2. Hard WCAG Contrast Enforcement Rules

When implementing UI components, Claude Code must adhere to these exact contrast pairings:

| Foreground Color | Background Color | Contrast Ratio | WCAG Rating | Status |
|---|---|---|---|---|
| `#041E10` (Dark Ink) | `#00EB79` (Electric Green) | **13.4:1** | AAA | **MANDATORY** for primary buttons |
| `#FFFFFF` (White) | `#00EB79` (Electric Green) | **1.5:1** | **FAIL** | **STRICTLY BANNED** |
| `#FFFFFF` (White) | `#008744` (Careem Green) | **4.6:1** | AA | Standard Light Mode CTA |
| `#F3F7F5` (Primary Text) | `#0F1613` (Dark Surface) | **16.5:1** | AAA | Standard Dark Mode Text |
| `#9FB3A8` (Secondary Text) | `#0F1613` (Dark Surface) | **8.4:1** | AAA | Secondary Dark Mode Subtext |
| `#465B50` (Secondary Text) | `#FFFFFF` (Light Surface) | **7.1:1** | AAA | Secondary Light Mode Subtext |

---

## 3. Typography & Surface Styling

### Typography
- **Headings & Display:** `Plus Jakarta Sans`, sans-serif (`font-weight: 600, 700, 800`)
- **Body & Controls:** `Inter`, system-ui, sans-serif (`font-weight: 400, 500, 600`)
- **Prices, Macros, Quantities:** `JetBrains Mono` or `Inter` with `font-variant-numeric: tabular-nums`

### Radii Scale (Careem Super-App Feel)
- **Cards & Drawers:** `20px` (`rounded-2xl`)
- **Pill Badges & CTAs:** `9999px` (`rounded-full`)
- **Form Inputs & Chips:** `14px` (`rounded-xl`)
- **Checkout Bottom Sheet:** `28px` top-left & top-right corners

### Futuristic Glassmorphism Effect
For floating bars, sub-navs, and checkout drawers in dark mode:
```css
background: rgba(15, 22, 19, 0.85);
backdrop-filter: blur(16px);
-webkit-backdrop-filter: blur(16px);
border: 1px solid rgba(0, 235, 121, 0.18);
box-shadow: 0 20px 40px rgba(0, 0, 0, 0.4);
```

---

## 4. Ready-to-Use CSS Custom Properties (`tokens.css`)

```css
:root {
  /* Dark Mode Default */
  --bg-base: #070B09;
  --bg-surface: #0F1613;
  --bg-elevated: #16211C;
  --border-subtle: #22322A;
  --border-glow: rgba(0, 235, 121, 0.22);

  --text-primary: #F3F7F5;
  --text-secondary: #9FB3A8;

  --brand-primary: #00EB79;
  --brand-hover: #2BFF96;
  --brand-on-primary: #041E10;

  --deal-bg: #2E2105;
  --deal-text: #FFC233;
  --allergen-bg: #331014;
  --allergen-text: #FF6B72;
  --ai-accent: #38BDF8;

  --font-display: 'Plus Jakarta Sans', system-ui, sans-serif;
  --font-body: 'Inter', system-ui, sans-serif;
  --font-mono: 'JetBrains Mono', monospace;

  --radius-card: 20px;
  --radius-input: 14px;
  --radius-pill: 9999px;
  --radius-sheet: 28px;
}

[data-theme="light"] {
  --bg-base: #F4F7F5;
  --bg-surface: #FFFFFF;
  --bg-elevated: #E9F2ED;
  --border-subtle: #D1DFD7;
  --border-glow: rgba(0, 135, 68, 0.18);

  --text-primary: #0D1B14;
  --text-secondary: #465B50;

  --brand-primary: #008744;
  --brand-hover: #007038;
  --brand-on-primary: #FFFFFF;

  --deal-bg: #FFF4D6;
  --deal-text: #8A5300;
  --allergen-bg: #FDECEC;
  --allergen-text: #B42318;
  --ai-accent: #026AA2;
}
```

---

## 5. Tailwind CSS Extension Config

Add this object inside your `tailwind.config.js` or `tailwind.config.ts`:

```javascript
module.exports = {
  theme: {
    extend: {
      colors: {
        careem: {
          dark: '#070B09',
          surface: '#0F1613',
          elevated: '#16211C',
          green: '#00EB79',
          'green-hover': '#2BFF96',
          'green-dark': '#008744',
          ink: '#041E10',
          muted: '#9FB3A8',
          border: '#22322A',
          deal: '#FFC233',
          'deal-bg': '#2E2105',
          allergen: '#FF6B72',
          'allergen-bg': '#331014',
        },
      },
      fontFamily: {
        display: ['Plus Jakarta Sans', 'sans-serif'],
        body: ['Inter', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
      borderRadius: {
        'card': '20px',
        'input': '14px',
        'sheet': '28px',
      },
      boxShadow: {
        'careem-glow': '0 0 25px rgba(0, 235, 121, 0.15)',
        'glass': '0 20px 40px rgba(0, 0, 0, 0.4)',
      },
    },
  },
};
```