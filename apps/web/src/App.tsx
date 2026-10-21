import React, { useState } from "react";
import { EstimateScreen } from "./components/EstimateScreen";
import { ContributionFlow } from "./components/ContributionFlow";
import { MyDataModal } from "./components/MyDataModal";

export function App(): React.JSX.Element {
  const [theme, setTheme] = useState<"light" | "dark">("light");
  const [showContribute, setShowContribute] = useState(false);
  const [showMyData, setShowMyData] = useState(false);

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
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:fixed focus:top-3 focus:left-3 focus:z-50 focus:px-4 focus:py-2.5 focus:bg-span focus:text-on-span focus:rounded-control focus:shadow-md focus:outline-none focus:ring-2 focus:ring-focus font-sans text-xs font-semibold"
      >
        Skip to main content
      </a>

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
              id="contribute-pay-btn"
              type="button"
              onClick={() => setShowContribute(true)}
              className="px-3 py-1.5 rounded-control border border-span bg-span text-on-span font-medium hover:opacity-90 focus:outline-none focus:ring-2 focus:ring-focus transition-colors"
              aria-haspopup="dialog"
            >
              Share your pay
            </button>
            <button
              id="my-data-btn"
              type="button"
              onClick={() => setShowMyData(true)}
              className="px-2.5 py-1 rounded-control border border-rule text-ink-2 hover:bg-sunken focus:outline-none focus:ring-2 focus:ring-focus transition-colors"
              aria-haspopup="dialog"
            >
              My Data
            </button>
            <button
              type="button"
              onClick={toggleTheme}
              className="px-2.5 py-1 rounded-control border border-rule-strong text-ink hover:bg-sunken focus:outline-none focus:ring-2 focus:ring-focus transition-colors"
            >
              {theme === "light" ? "Dark mode" : "Light mode"}
            </button>
            <span className="font-medium text-ink">INR (Rs)</span>
          </div>
        </div>
      </header>

      <main id="main-content" tabIndex={-1} className="focus:outline-none">
        <EstimateScreen />
      </main>

      <footer className="max-w-content mx-auto px-4 sm:px-8 mt-12 py-6 border-t border-rule text-xs font-sans text-ink-3 flex flex-col sm:flex-row justify-between gap-2">
        <p>
          ArthaIQ statistical estimates are calibrated to 80% nominal coverage (ADR-0005).
        </p>
        <p>
          Built for working professionals in India technology hubs.
        </p>
      </footer>

      {showContribute && (
        <div
          className="modal-overlay"
          role="dialog"
          aria-modal="true"
          aria-label="Contribute your pay data"
        >
          <div className="modal-backdrop" onClick={() => setShowContribute(false)} aria-hidden="true" />
          <div className="modal-panel">
            <button
              type="button"
              className="modal-close-btn"
              onClick={() => setShowContribute(false)}
              aria-label="Close contribution form"
            >
              X
            </button>
            <ContributionFlow
              onClose={() => setShowContribute(false)}
              onComplete={() => setShowContribute(false)}
            />
          </div>
        </div>
      )}

      {showMyData && (
        <MyDataModal onClose={() => setShowMyData(false)} />
      )}
    </div>
  );
}

export default App;
