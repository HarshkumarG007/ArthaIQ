import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: ["class", '[data-theme="dark"]'],
  theme: {
    extend: {
      colors: {
        paper: "var(--paper)",
        sheet: "var(--sheet)",
        sunken: "var(--sunken)",
        rule: "var(--rule)",
        "rule-strong": "var(--rule-strong)",
        ink: "var(--ink)",
        "ink-2": "var(--ink-2)",
        "ink-3": "var(--ink-3)",
        span: "var(--span)",
        "span-strong": "var(--span-strong)",
        "span-wash": "var(--span-wash)",
        "on-span": "var(--on-span)",
        ok: "var(--ok)",
        "ok-wash": "var(--ok-wash)",
        caution: "var(--caution)",
        "caution-wash": "var(--caution-wash)",
        alert: "var(--alert)",
        "alert-wash": "var(--alert-wash)",
        focus: "var(--focus)",

        /* shadcn semantic tokens */
        background: "var(--background)",
        foreground: "var(--foreground)",
        card: {
          DEFAULT: "var(--card)",
          foreground: "var(--card-foreground)",
        },
        popover: {
          DEFAULT: "var(--popover)",
          foreground: "var(--popover-foreground)",
        },
        primary: {
          DEFAULT: "var(--primary)",
          foreground: "var(--primary-foreground)",
        },
        secondary: {
          DEFAULT: "var(--secondary)",
          foreground: "var(--secondary-foreground)",
        },
        muted: {
          DEFAULT: "var(--muted)",
          foreground: "var(--muted-foreground)",
        },
        accent: {
          DEFAULT: "var(--accent)",
          foreground: "var(--accent-foreground)",
        },
        destructive: {
          DEFAULT: "var(--destructive)",
          foreground: "var(--destructive-foreground)",
        },
        border: "var(--border)",
        input: "var(--input)",
        ring: "var(--ring)",
      },
      borderRadius: {
        control: "var(--radius-control)",
        dialog: "var(--radius-dialog)",
        DEFAULT: "var(--radius-control)",
      },
      fontFamily: {
        serif: ["var(--font-serif)"],
        sans: ["var(--font-sans)"],
      },
      maxWidth: {
        content: "1120px",
      },
      transitionDuration: {
        state: "120ms",
        span: "220ms",
      },
    },
  },
  plugins: [],
};

export default config;
