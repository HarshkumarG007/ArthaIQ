import React, { useState } from "react";
import { formatMoney, formatRange } from "./lib/formatMoney";
import { RangeSpan, RangeSpanState } from "./components/RangeSpan";

export function App(): React.JSX.Element {
  const [activeState, setActiveState] = useState<RangeSpanState>("default");
  const [showCompare, setShowCompare] = useState<boolean>(true);
  const [showPrevious, setShowPrevious] = useState<boolean>(false);
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
    <div className="min-h-screen bg-paper text-ink p-4 sm:p-8 transition-colors">
      <header className="max-w-content mx-auto border-b border-rule pb-4 mb-8 flex justify-between items-center">
        <div>
          <h1 className="text-xl font-serif font-semibold tracking-tight text-ink">
            ArthaIQ
          </h1>
          <p className="text-sm font-sans text-ink-2">
            India Tech Compensation Intelligence
          </p>
        </div>
        <div className="flex items-center gap-4 text-xs font-sans text-ink-3">
          <button
            type="button"
            onClick={toggleTheme}
            className="px-2.5 py-1 rounded-control border border-rule-strong text-ink hover:bg-sunken focus:outline-none focus:ring-2 focus:ring-focus"
          >
            {theme === "light" ? "Dark mode" : "Light mode"}
          </button>
          <span>INR</span>
        </div>
      </header>

      <main className="max-w-content mx-auto flex flex-col gap-8">
        {/* Estimate Headline section (design.md section 8) */}
        <section className="bg-sheet rounded-control border border-rule p-6">
          <div className="mb-6">
            <h2 className="text-xs font-sans font-semibold uppercase tracking-wider text-ink-3 mb-1">
              Estimated range
            </h2>
            <div className="text-3xl sm:text-4xl font-serif font-semibold text-ink mb-1">
              {formatRange(24.5, 55.0)}
            </div>
            <p className="text-sm font-sans text-ink-2">
              Typical: <span className="font-serif font-semibold text-ink">{formatMoney(38.0)}</span>
            </p>
            <p className="text-xs font-sans text-ink-3 mt-1.5">
              Guaranteed cash, before tax, in rupees, as of October 2026.
            </p>
          </div>

          {/* Interactive controls for design review */}
          <div className="mb-6 flex flex-wrap items-center gap-2 border-y border-rule py-3">
            <span className="text-xs font-sans font-medium text-ink-3 mr-2">
              Component State:
            </span>
            {(
              [
                "default",
                "limited_evidence",
                "loading",
                "abstained",
                "stale",
              ] as RangeSpanState[]
            ).map((s) => (
              <button
                key={s}
                type="button"
                onClick={() => setActiveState(s)}
                className={`px-2.5 py-1 rounded-control text-xs font-sans font-medium transition-colors ${
                  activeState === s
                    ? "bg-span text-on-span"
                    : "bg-sheet border border-rule text-ink hover:bg-sunken"
                }`}
              >
                {s.replace("_", " ")}
              </button>
            ))}

            <div className="h-4 w-[1px] bg-rule mx-1 hidden sm:block" />

            <label className="inline-flex items-center gap-1.5 text-xs font-sans text-ink-2 cursor-pointer ml-auto">
              <input
                type="checkbox"
                checked={showCompare}
                onChange={(e) => setShowCompare(e.target.checked)}
                className="rounded border-rule-strong text-span focus:ring-focus"
              />
              Show your figure (32L)
            </label>

            <label className="inline-flex items-center gap-1.5 text-xs font-sans text-ink-2 cursor-pointer">
              <input
                type="checkbox"
                checked={showPrevious}
                onChange={(e) => setShowPrevious(e.target.checked)}
                className="rounded border-rule-strong text-span focus:ring-focus"
              />
              Show ghost span (Before)
            </label>
          </div>

          {/* RangeSpan Component */}
          <RangeSpan
            p10={24.5}
            p50={38.0}
            p90={55.0}
            currency="INR"
            unit="lpa"
            state={activeState}
            compareValue={showCompare ? 32.0 : undefined}
            previous={
              showPrevious
                ? { p10: 20.0, p50: 32.0, p90: 48.0 }
                : undefined
            }
            measure="Guaranteed cash"
            date="as of October 2026"
          />
        </section>

        <section className="border-t border-rule pt-4 text-xs font-sans text-ink-3">
          <p>
            ArthaIQ statistical ranges are calibrated to 80% nominal coverage.
            No lone numbers. No false precision.
          </p>
        </section>
      </main>
    </div>
  );
}

export default App;
