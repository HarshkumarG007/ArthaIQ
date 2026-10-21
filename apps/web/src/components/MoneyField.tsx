import React, { useState } from "react";
import { formatIndianGrouping, formatWesternGrouping } from "../lib/formatMoney";

export type PayPeriod = "annual" | "monthly";
export type CompensationMeasureType =
  | "guaranteed_cash"
  | "ctc"
  | "in_hand"
  | "total_with_bonus"
  | "not_sure";

export interface MoneyFieldProps {
  label?: string;
  helperText?: string;
  value?: number | null; // stored in LPA
  currency?: string;
  onChange: (valLpa: number | null, period: PayPeriod, measureType: CompensationMeasureType) => void;
  className?: string;
}

export const MEASURE_OPTIONS: Array<{ id: CompensationMeasureType; label: string; hint: string }> = [
  {
    id: "guaranteed_cash",
    label: "Fixed base cash pay (matches estimate)",
    hint: "Contractual annual cash allowances paid unconditionally before tax.",
  },
  {
    id: "ctc",
    label: "Total CTC (Cost to Company)",
    hint: "Includes employer PF, gratuity, insurance, and variable target bonus.",
  },
  {
    id: "in_hand",
    label: "Monthly take-home / in-hand cash",
    hint: "Net cash deposited into your bank account after tax and PF deductions.",
  },
  {
    id: "total_with_bonus",
    label: "Base pay + realized cash bonus",
    hint: "Fixed cash plus variable annual performance incentive.",
  },
  {
    id: "not_sure",
    label: "Not sure / rough estimate",
    hint: "We will treat your figure as an approximate reference point.",
  },
];

/**
 * MoneyField — Accessible compensation input field with Indian grouping and measure helper.
 * Per design.md section 8:
 * "Currency prefix; Indian grouping as the user types; explicit per-year or per-month toggle;
 * 'Which figure is this?' helper: fixed pay, CTC, in-hand, total including bonus, with plain explanations."
 */
export function MoneyField({
  label = "Your compensation figure",
  helperText = "Enter your current pay to compare against the estimated market cohort.",
  value,
  currency = "INR",
  onChange,
  className = "",
}: MoneyFieldProps): React.JSX.Element {
  const [period, setPeriod] = useState<PayPeriod>("annual");
  const [measureType, setMeasureType] = useState<CompensationMeasureType>("guaranteed_cash");
  const [rawText, setRawText] = useState<string>(() => {
    if (value !== undefined && value !== null && !isNaN(value)) {
      // Nominal rupees
      const nominal = Math.round(value * 100000);
      return currency === "INR" ? formatIndianGrouping(nominal) : formatWesternGrouping(nominal);
    }
    return "";
  });

  const isINR = currency.toUpperCase() === "INR";
  const currencySymbol = isINR ? "₹" : "$";

  const handleTextChange = (e: React.ChangeEvent<HTMLInputElement>): void => {
    const input = e.target.value;
    // Strip non-digits except decimal point
    const cleanDigits = input.replace(/[^0-9.]/g, "");

    if (cleanDigits === "") {
      setRawText("");
      onChange(null, period, measureType);
      return;
    }

    const numVal = parseFloat(cleanDigits);
    if (!isNaN(numVal)) {
      // Format grouping as user types (only format integer part while preserving typing decimal)
      const parts = cleanDigits.split(".");
      const intPart = parts[0] || "0";
      const formattedInt = isINR ? formatIndianGrouping(intPart) : formatWesternGrouping(intPart);
      const displayStr = parts.length > 1 ? `${formattedInt}.${parts[1]}` : formattedInt;

      setRawText(displayStr);

      // Convert to annualized LPA
      const annualNominal = period === "monthly" ? numVal * 12 : numVal;
      const lpaVal = Math.round((annualNominal / 100000) * 100) / 100;
      onChange(lpaVal, period, measureType);
    } else {
      setRawText(input);
    }
  };

  const handlePeriodToggle = (newPeriod: PayPeriod): void => {
    setPeriod(newPeriod);
    const cleanDigits = rawText.replace(/[^0-9.]/g, "");
    const numVal = parseFloat(cleanDigits);
    if (!isNaN(numVal)) {
      const annualNominal = newPeriod === "monthly" ? numVal * 12 : numVal;
      const lpaVal = Math.round((annualNominal / 100000) * 100) / 100;
      onChange(lpaVal, newPeriod, measureType);
    }
  };

  const handleMeasureChange = (newMeasure: CompensationMeasureType): void => {
    setMeasureType(newMeasure);
    const cleanDigits = rawText.replace(/[^0-9.]/g, "");
    const numVal = parseFloat(cleanDigits);
    const annualNominal = !isNaN(numVal) ? (period === "monthly" ? numVal * 12 : numVal) : null;
    const lpaVal = annualNominal !== null ? Math.round((annualNominal / 100000) * 100) / 100 : null;
    onChange(lpaVal, period, newMeasure);
  };

  return (
    <div data-testid="money-field" className={`flex flex-col gap-3 text-left ${className}`}>
      <div className="flex flex-col gap-1">
        <label htmlFor="money-field-input" className="text-xs font-sans font-medium text-ink">
          {label}
        </label>
        {helperText && (
          <p id="money-field-helper" className="text-[11px] font-sans text-ink-3">
            {helperText}
          </p>
        )}
      </div>

      {/* Input Group with Currency Prefix and Period Toggle */}
      <div className="flex items-center gap-2">
        <div className="relative flex-1">
          <span
            aria-hidden="true"
            className="absolute left-3 top-1/2 -translate-y-1/2 text-sm font-sans font-medium text-ink-3 pointer-events-none select-none"
          >
            {currencySymbol}
          </span>
          <input
            id="money-field-input"
            type="text"
            inputMode="decimal"
            value={rawText}
            onChange={handleTextChange}
            placeholder={period === "annual" ? "e.g. 28,00,000" : "e.g. 2,30,000"}
            aria-describedby="money-field-helper"
            className="w-full pl-8 pr-3 py-2.5 bg-sheet border border-rule-strong rounded-control text-sm font-sans text-ink font-medium tabular-nums focus:outline-none focus:ring-2 focus:ring-focus min-h-[44px]"
          />
        </div>

        {/* Per-year / Per-month Toggle Buttons */}
        <div className="flex rounded-control border border-rule-strong p-0.5 bg-sheet shrink-0">
          <button
            type="button"
            onClick={() => handlePeriodToggle("annual")}
            className={`px-2.5 py-1.5 text-xs font-sans font-medium rounded-sm min-h-[40px] transition-colors ${
              period === "annual" ? "bg-span text-on-span" : "text-ink-2 hover:bg-sunken"
            }`}
          >
            / year
          </button>
          <button
            type="button"
            onClick={() => handlePeriodToggle("monthly")}
            className={`px-2.5 py-1.5 text-xs font-sans font-medium rounded-sm min-h-[40px] transition-colors ${
              period === "monthly" ? "bg-span text-on-span" : "text-ink-2 hover:bg-sunken"
            }`}
          >
            / month
          </button>
        </div>
      </div>

      {/* "Which figure is this?" Helper */}
      <div className="flex flex-col gap-1 mt-1">
        <label htmlFor="measure-type-select" className="text-xs font-sans font-medium text-ink-2">
          Which figure is this?
        </label>
        <select
          id="measure-type-select"
          value={measureType}
          onChange={(e) => handleMeasureChange(e.target.value as CompensationMeasureType)}
          className="w-full px-3 py-2 bg-sheet border border-rule-strong rounded-control text-xs font-sans text-ink focus:outline-none focus:ring-2 focus:ring-focus min-h-[44px]"
        >
          {MEASURE_OPTIONS.map((opt) => (
            <option key={opt.id} value={opt.id}>
              {opt.label}
            </option>
          ))}
        </select>
        <p className="text-[11px] font-sans text-ink-3">
          {MEASURE_OPTIONS.find((o) => o.id === measureType)?.hint}
        </p>
      </div>
    </div>
  );
}

export default MoneyField;
