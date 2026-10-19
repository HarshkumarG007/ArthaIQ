import React from "react";
import { formatMoney, formatRange } from "./lib/formatMoney";

export function App(): React.JSX.Element {
  return (
    <div className="min-h-screen bg-paper text-ink p-8">
      <header className="max-w-content mx-auto border-b border-rule pb-4 mb-8 flex justify-between items-center">
        <div>
          <h1 className="text-xl font-serif font-semibold tracking-tight text-ink">
            ArthaIQ
          </h1>
          <p className="text-sm text-ink-2">
            India Tech Compensation Intelligence
          </p>
        </div>
        <div className="flex items-center gap-4 text-xs font-sans text-ink-3">
          <span>INR</span>
          <span className="text-rule">|</span>
          <span>USD</span>
        </div>
      </header>

      <main className="max-w-content mx-auto">
        <section className="mb-8">
          <h2 className="text-sm font-sans font-semibold text-ink-2 mb-2">
            Estimated range
          </h2>
          <div className="text-3xl font-serif font-semibold figure text-ink mb-1">
            {formatRange(12.5, 18.0)}
          </div>
          <p className="text-base text-ink-2">
            Typical: <span className="figure font-semibold">{formatMoney(15.0)}</span>
          </p>
          <p className="text-xs text-ink-3 mt-2">
            Fixed annual cash pay, before tax, in rupees.
          </p>
        </section>

        <section className="border-t border-rule pt-6 text-xs text-ink-3">
          <p>
            This range is an estimate from data of varying quality. It is not an offer,
            appraisal or guarantee.
          </p>
        </section>
      </main>
    </div>
  );
}

export default App;
