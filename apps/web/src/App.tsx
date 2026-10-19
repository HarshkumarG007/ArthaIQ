import React, { useState } from "react";
import { EstimateScreen } from "./components/EstimateScreen";

export function App(): React.JSX.Element {
  const [theme, setTheme] = useState<"light" | "dark">("light");

  const toggleTheme = (): void => {
    const nextTheme = theme === "light" ? "dark" : "light";
    setTheme(nextTheme);
    if (nextTheme === "dark") {
      document.documentElement.setAttribute("data-theme", "dark");
    } else {
      document.documentElement.removeAttribute("data-theme");
    }
  };

  return (
    <div className="min-h-screen bg-paper text-ink transition-colors selection:bg-span-wash selection:text-span-strong">
      {/* Global Header */}
      <header className="border-b border-rule bg-sheet">
        <div className="max-w-content mx-auto px-4 sm:px-8 py-4 flex justify-between items-center">
          <div>
            <h1 className="text-xl font-serif font-semibold tracking-tight text-ink">
              ArthaIQ
            </h1>
            <p className="text-xs font-sans text-ink-2">
              India Tech Compensation Intelligence
            </p>
          </div>
          <div className="flex items-center gap-4 text-xs font-sans text-ink-3">
            <button
              type="button"
              onClick={toggleTheme}
              className="px-2.5 py-1 rounded-control border border-rule-strong text-ink hover:bg-sunken focus:outline-none focus:ring-2 focus:ring-focus transition-colors"
            >
              {theme === "light" ? "Dark mode" : "Light mode"}
            </button>
            <span className="font-medium text-ink">INR (₹)</span>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main>
        <EstimateScreen />
      </main>

      {/* Global Footer */}
      <footer className="max-w-content mx-auto px-4 sm:px-8 mt-12 py-6 border-t border-rule text-xs font-sans text-ink-3 flex flex-col sm:flex-row justify-between gap-2">
        <p>
          ArthaIQ statistical estimates are calibrated to 80% nominal coverage (ADR-0005).
        </p>
        <p>
          Built for working professionals in India technology hubs.
        </p>
      </footer>
    </div>
  );
}

export default App;
