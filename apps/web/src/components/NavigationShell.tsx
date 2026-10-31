import React, { useState, useEffect } from "react";
import { EstimateScreen } from "./EstimateScreen";
import { CareerRoute, type CareerSubView } from "../routes/career";
import { PilotRoute } from "../routes/pilot";
import { ContributionFlow } from "./ContributionFlow";
import { MyDataModal } from "./MyDataModal";
import {
  TrendingUp,
  Compass,
  Activity,
  PlusCircle,
  Shield,
  Sun,
  Moon,
} from "lucide-react";

export type AppNavMode = "compensation" | "career" | "pilot";

interface NavigationShellProps {
  initialMode?: AppNavMode;
}

export function NavigationShell({
  initialMode = "compensation",
}: NavigationShellProps): React.JSX.Element {
  const [mode, setMode] = useState<AppNavMode>(initialMode);
  const [careerSubView, setCareerSubView] = useState<CareerSubView>("skills");
  const [theme, setTheme] = useState<"light" | "dark">("light");
  const [showContribute, setShowContribute] = useState(false);
  const [showMyData, setShowMyData] = useState(false);

  // Hash route synchronization
  useEffect(() => {
    const handleHashChange = (): void => {
      const hash = window.location.hash.toLowerCase();
      if (hash.startsWith("#career")) {
        setMode("career");
        if (hash.includes("/plan")) setCareerSubView("plan");
        else if (hash.includes("/practice")) setCareerSubView("practice");
        else if (hash.includes("/ledger")) setCareerSubView("ledger");
        else setCareerSubView("skills");
      } else if (hash.startsWith("#pilot")) {
        setMode("pilot");
      } else if (hash.startsWith("#compensation")) {
        setMode("compensation");
      }
    };

    handleHashChange();
    window.addEventListener("hashchange", handleHashChange);
    return () => window.removeEventListener("hashchange", handleHashChange);
  }, []);

  const navigateTo = (nextMode: AppNavMode, sub?: CareerSubView): void => {
    setMode(nextMode);
    if (nextMode === "career") {
      const subPath = sub || careerSubView;
      window.location.hash = `#career/${subPath}`;
    } else if (nextMode === "pilot") {
      window.location.hash = "#pilot";
    } else {
      window.location.hash = "#compensation";
    }
  };

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
    <div className="min-h-screen bg-paper text-ink transition-colors flex flex-col md:flex-row">
      {/* Skip to Main Content Link (WCAG 2.1 A) */}
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:fixed focus:top-3 focus:left-3 focus:z-50 focus:px-4 focus:py-2.5 focus:bg-span focus:text-on-span focus:rounded-control focus:shadow-md focus:outline-none focus:ring-2 focus:ring-focus font-sans text-xs font-semibold"
      >
        Skip to main content
      </a>

      {/* Desktop Side Rail Navigation (>= 768px) */}
      <aside
        className="hidden md:flex flex-col w-64 border-r border-rule bg-sheet shrink-0 min-h-screen sticky top-0"
        aria-label="Desktop Sidebar Navigation"
      >
        {/* Brand / Logo */}
        <div className="p-6 border-b border-rule">
          <div className="flex items-center gap-2">
            <h1 className="text-xl font-serif font-bold text-ink tracking-tight">
              ArthaIQ
            </h1>
            <span className="text-2xs px-2 py-0.5 rounded font-mono font-semibold bg-span-wash text-span-strong">
              v1.0
            </span>
          </div>
          <p className="text-xs font-sans text-ink-2 mt-0.5">
            Ethical Intelligence for India Tech
          </p>
        </div>

        {/* Primary Navigation Rail */}
        <nav
          className="p-4 space-y-2 flex-1"
          aria-label="Main Navigation"
        >
          <button
            type="button"
            id="nav-compensation-btn"
            onClick={() => navigateTo("compensation")}
            aria-current={mode === "compensation" ? "page" : undefined}
            className={`w-full flex items-center gap-3 px-3.5 py-2.5 rounded-control text-sm font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-focus ${
              mode === "compensation"
                ? "bg-span text-on-span shadow-sm"
                : "text-ink hover:bg-sunken border border-transparent"
            }`}
          >
            <TrendingUp className="w-4 h-4 shrink-0" aria-hidden="true" />
            <span>Compensation</span>
          </button>

          <button
            type="button"
            id="nav-career-btn"
            onClick={() => navigateTo("career")}
            aria-current={mode === "career" ? "page" : undefined}
            className={`w-full flex items-center justify-between px-3.5 py-2.5 rounded-control text-sm font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-focus ${
              mode === "career"
                ? "bg-span text-on-span shadow-sm"
                : "text-ink hover:bg-sunken border border-transparent"
            }`}
          >
            <div className="flex items-center gap-3">
              <Compass className="w-4 h-4 shrink-0" aria-hidden="true" />
              <span>Career Architect</span>
            </div>
            <span
              className={`text-2xs px-1.5 py-0.5 rounded font-mono font-medium ${
                mode === "career"
                  ? "bg-on-span text-span"
                  : "bg-sunken text-ink-2"
              }`}
            >
              Local
            </span>
          </button>

          <button
            type="button"
            id="nav-pilot-btn"
            onClick={() => navigateTo("pilot")}
            aria-current={mode === "pilot" ? "page" : undefined}
            className={`w-full flex items-center justify-between px-3.5 py-2.5 rounded-control text-sm font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-focus ${
              mode === "pilot"
                ? "bg-span text-on-span shadow-sm"
                : "text-ink hover:bg-sunken border border-transparent"
            }`}
          >
            <div className="flex items-center gap-3">
              <Activity className="w-4 h-4 shrink-0" aria-hidden="true" />
              <span>Pilot Telemetry</span>
            </div>
            <span
              className={`text-2xs px-1.5 py-0.5 rounded font-mono font-medium ${
                mode === "pilot"
                  ? "bg-on-span text-span"
                  : "bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300"
              }`}
            >
              N=150
            </span>
          </button>
        </nav>

        {/* Rail Footer Controls */}
        <div className="p-4 border-t border-rule space-y-3">
          <button
            id="rail-contribute-btn"
            type="button"
            onClick={() => setShowContribute(true)}
            className="w-full flex items-center justify-center gap-2 px-3 py-2 rounded-control border border-rule text-ink-2 hover:bg-sunken text-xs font-semibold focus:outline-none focus:ring-2 focus:ring-focus transition-colors"
            aria-haspopup="dialog"
          >
            <PlusCircle className="w-3.5 h-3.5" aria-hidden="true" />
            <span>Share your pay</span>
          </button>

          <div className="flex items-center justify-between pt-1">
            <button
              id="rail-my-data-btn"
              type="button"
              onClick={() => setShowMyData(true)}
              className="flex items-center gap-1.5 px-2.5 py-1 rounded-control border border-rule text-ink-2 hover:bg-sunken text-xs font-medium focus:outline-none focus:ring-2 focus:ring-focus transition-colors"
              aria-haspopup="dialog"
            >
              <Shield className="w-3.5 h-3.5" aria-hidden="true" />
              <span>My Data</span>
            </button>

            <button
              type="button"
              onClick={toggleTheme}
              className="p-1.5 rounded-control border border-rule text-ink hover:bg-sunken focus:outline-none focus:ring-2 focus:ring-focus transition-colors"
              aria-label={theme === "light" ? "Switch to dark mode" : "Switch to light mode"}
            >
              {theme === "light" ? (
                <Moon className="w-4 h-4" aria-hidden="true" />
              ) : (
                <Sun className="w-4 h-4" aria-hidden="true" />
              )}
            </button>
          </div>

          <div className="text-2xs text-ink-3 pt-1 border-t border-rule flex justify-between items-center">
            <span>Currency: INR (₹)</span>
            <span>80% CQR nominal</span>
          </div>
        </div>
      </aside>

      {/* Mobile Top Header (< 768px) */}
      <header className="md:hidden border-b border-rule bg-sheet px-4 py-3 flex justify-between items-center">
        <div>
          <h1 className="text-lg font-serif font-bold text-ink">ArthaIQ</h1>
          <p className="text-2xs font-sans text-ink-2">Compensation & Career</p>
        </div>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={toggleTheme}
            className="p-2 rounded-control border border-rule text-ink hover:bg-sunken focus:outline-none focus:ring-2 focus:ring-focus"
            aria-label={theme === "light" ? "Switch to dark mode" : "Switch to light mode"}
          >
            {theme === "light" ? <Moon className="w-4 h-4" /> : <Sun className="w-4 h-4" />}
          </button>
          <button
            type="button"
            onClick={() => setShowMyData(true)}
            className="px-2.5 py-1 rounded-control border border-rule text-ink-2 text-xs font-medium focus:outline-none focus:ring-2 focus:ring-focus"
          >
            My Data
          </button>
        </div>
      </header>

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0 pb-20 md:pb-0">
        <main
          id="main-content"
          tabIndex={-1}
          className="focus:outline-none flex-1 max-w-content mx-auto w-full p-4 sm:p-8"
        >
          {mode === "compensation" ? (
            <EstimateScreen />
          ) : mode === "career" ? (
            <CareerRoute
              initialSubView={careerSubView}
              onSubViewChange={(view) => {
                setCareerSubView(view);
                window.location.hash = `#career/${view}`;
              }}
            />
          ) : (
            <PilotRoute
              onNavigateToCareer={() => navigateTo("career")}
              onNavigateToCompensation={() => navigateTo("compensation")}
            />
          )}
        </main>

        {/* Global Footer */}
        <footer className="max-w-content mx-auto w-full px-4 sm:px-8 py-6 border-t border-rule text-xs font-sans text-ink-3 flex flex-col sm:flex-row justify-between gap-2 mt-auto">
          <p>
            ArthaIQ statistical estimates are calibrated to 80% nominal coverage (ADR-0005).
          </p>
          <p>
            Local-first career intelligence · 0 server profile retention (ADR-0012, DPDP Act 2023).
          </p>
        </footer>
      </div>

      {/* Mobile Fixed Bottom Navigation Bar (< 768px) */}
      <nav
        className="md:hidden fixed bottom-0 left-0 right-0 z-40 bg-sheet border-t border-rule flex justify-around items-center h-16 px-2"
        aria-label="Mobile Bottom Navigation"
      >
        <button
          type="button"
          id="mobile-nav-compensation-btn"
          onClick={() => navigateTo("compensation")}
          aria-current={mode === "compensation" ? "page" : undefined}
          className={`flex flex-col items-center justify-center w-16 h-12 rounded-control text-xs font-medium focus:outline-none focus:ring-2 focus:ring-focus ${
            mode === "compensation" ? "text-span font-bold" : "text-ink-2 hover:text-ink"
          }`}
        >
          <TrendingUp className="w-5 h-5" aria-hidden="true" />
          <span className="text-2xs mt-0.5">Pay</span>
        </button>

        <button
          type="button"
          id="mobile-nav-career-btn"
          onClick={() => navigateTo("career")}
          aria-current={mode === "career" ? "page" : undefined}
          className={`flex flex-col items-center justify-center w-14 h-12 rounded-control text-xs font-medium focus:outline-none focus:ring-2 focus:ring-focus ${
            mode === "career" ? "text-span font-bold" : "text-ink-2 hover:text-ink"
          }`}
        >
          <Compass className="w-5 h-5" aria-hidden="true" />
          <span className="text-2xs mt-0.5">Career</span>
        </button>

        <button
          type="button"
          id="mobile-nav-pilot-btn"
          onClick={() => navigateTo("pilot")}
          aria-current={mode === "pilot" ? "page" : undefined}
          className={`flex flex-col items-center justify-center w-14 h-12 rounded-control text-xs font-medium focus:outline-none focus:ring-2 focus:ring-focus ${
            mode === "pilot" ? "text-span font-bold" : "text-ink-2 hover:text-ink"
          }`}
        >
          <Activity className="w-5 h-5" aria-hidden="true" />
          <span className="text-2xs mt-0.5">Pilot</span>
        </button>

        <button
          type="button"
          id="mobile-nav-contribute-btn"
          onClick={() => setShowContribute(true)}
          className="flex flex-col items-center justify-center w-16 h-12 rounded-control text-xs font-medium text-ink-2 hover:text-ink focus:outline-none focus:ring-2 focus:ring-focus"
          aria-haspopup="dialog"
        >
          <PlusCircle className="w-5 h-5" aria-hidden="true" />
          <span className="text-2xs mt-0.5">Share</span>
        </button>

        <button
          type="button"
          id="mobile-nav-my-data-btn"
          onClick={() => setShowMyData(true)}
          className="flex flex-col items-center justify-center w-16 h-12 rounded-control text-xs font-medium text-ink-2 hover:text-ink focus:outline-none focus:ring-2 focus:ring-focus"
          aria-haspopup="dialog"
        >
          <Shield className="w-5 h-5" aria-hidden="true" />
          <span className="text-2xs mt-0.5">Privacy</span>
        </button>
      </nav>

      {/* Contribution Flow Modal Dialog */}
      {showContribute && (
        <div
          className="modal-overlay"
          role="dialog"
          aria-modal="true"
          aria-label="Contribute your pay data"
        >
          <div
            className="modal-backdrop"
            onClick={() => setShowContribute(false)}
            aria-hidden="true"
          />
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

      {/* My Data Modal Dialog */}
      {showMyData && (
        <MyDataModal onClose={() => setShowMyData(false)} />
      )}
    </div>
  );
}

export default NavigationShell;

