/**
 * ArthaIQ Money and Currency Formatter (T9.07, ADR-0007, design.md section 8).
 *
 * Adheres strictly to:
 * - Rule R-UI-06: Format all money and dates through the shared formatter.
 * - Principle DP-4: No false precision. Round to a granularity the range can justify.
 * - Principle DP-10: Local numbers. Indian grouping and lakh shorthand are first-class.
 * - design.md section 8:
 *   "INR in lakh to one decimal (crore from 100 lakh), table cells in full Indian grouping
 *    (1,23,456, not 123,456), USD with thousands separators. Display rounding defaults:
 *    INR to 0.1 lakh, USD to $1,000. Never imply precision finer than the range supports.
 *    Do not rely on browser compact-number notation for lakh; test the formatter."
 */

export type CurrencyCode = "INR" | "USD" | string;
export type MoneyUnit = "lpa" | "rupees" | "raw";
export type MoneyStyle = "headline" | "compact" | "full" | "table";

export interface MoneyFormatOptions {
  currency?: CurrencyCode;
  unit?: MoneyUnit; // 'lpa' (default for INR model outputs), 'rupees' (nominal raw pay), 'raw'
  style?: MoneyStyle; // 'headline' ('₹12.5 lakh'), 'full' ('₹1,23,456'), 'table' ('1,23,456')
  includeSymbol?: boolean; // whether to prefix ₹ or $ (default true except for table style)
  includeUnit?: boolean; // whether to append 'lakh' or 'crore' in compact/headline (default true)
  decimals?: number; // custom decimal override
}

/**
 * Formats a number with Indian digit grouping:
 * Rightmost 3 digits group together, then groups of 2 digits moving left.
 * Example: 1234567 -> "12,34,567"
 * Example: 10000000 -> "1,00,00,000"
 */
export function formatIndianGrouping(value: number | string): string {
  if (value === null || value === undefined || value === "") {
    return "0";
  }

  const numStr = String(value).trim();
  const isNegative = numStr.startsWith("-");
  const cleanStr = isNegative ? numStr.slice(1) : numStr;

  const [integerPart = "0", decimalPart] = cleanStr.split(".");

  if (integerPart.length <= 3) {
    const formatted = integerPart + (decimalPart !== undefined ? `.${decimalPart}` : "");
    return isNegative ? `-${formatted}` : formatted;
  }

  // Last 3 digits
  const lastThree = integerPart.slice(-3);
  const remaining = integerPart.slice(0, -3);

  // Group remaining digits by 2 from right to left
  const otherGroups: string[] = [];
  let currentGroup = "";
  for (let i = remaining.length - 1; i >= 0; i--) {
    currentGroup = remaining[i] + currentGroup;
    if (currentGroup.length === 2 || i === 0) {
      otherGroups.unshift(currentGroup);
      currentGroup = "";
    }
  }

  const formattedInt = `${otherGroups.join(",")},${lastThree}`;
  const result = decimalPart !== undefined ? `${formattedInt}.${decimalPart}` : formattedInt;

  return isNegative ? `-${result}` : result;
}

/**
 * Formats a number with standard Western thousand separators (for USD).
 * Example: 1234567 -> "1,234,567"
 */
export function formatWesternGrouping(value: number | string): string {
  if (value === null || value === undefined || value === "") {
    return "0";
  }

  const numStr = String(value).trim();
  const isNegative = numStr.startsWith("-");
  const cleanStr = isNegative ? numStr.slice(1) : numStr;

  const [integerPart = "0", decimalPart] = cleanStr.split(".");

  const formattedInt = integerPart.replace(/\B(?=(\d{3})+(?!\d))/g, ",");
  const result = decimalPart !== undefined ? `${formattedInt}.${decimalPart}` : formattedInt;

  return isNegative ? `-${result}` : result;
}

/**
 * Rounds a number to a specified number of decimal places using half-up arithmetic.
 */
function roundToPrecision(val: number, decimals: number): number {
  const factor = Math.pow(10, decimals);
  return Math.round((val + Number.EPSILON) * factor) / factor;
}

/**
 * Format compensation money amounts according to ArthaIQ design system rules.
 */
export function formatMoney(amount: number | null | undefined, options: MoneyFormatOptions = {}): string {
  if (amount === null || amount === undefined || isNaN(amount)) {
    return "—";
  }

  const {
    currency = "INR",
    unit = "lpa",
    style = "headline",
    includeSymbol = style !== "table",
    includeUnit = true,
    decimals,
  } = options;

  const isINR = currency.toUpperCase() === "INR";
  const symbol = isINR ? "₹" : currency.toUpperCase() === "USD" ? "$" : `${currency} `;
  const isNegative = amount < 0;
  const absAmount = Math.abs(amount);

  // 1. Table style: unrounded full precision or standard grouping without currency symbol (by default)
  if (style === "table") {
    const grouped = isINR
      ? formatIndianGrouping(Math.round(absAmount))
      : formatWesternGrouping(Math.round(absAmount));
    const prefix = includeSymbol ? symbol : "";
    return isNegative ? `-${prefix}${grouped}` : `${prefix}${grouped}`;
  }

  // 2. Full style: full nominal amount with currency symbol and local digit grouping
  if (style === "full") {
    // If input is in LPA, convert to nominal rupees
    const nominal = unit === "lpa" && isINR ? absAmount * 100000 : absAmount;
    const rounded = Math.round(nominal);
    const grouped = isINR ? formatIndianGrouping(rounded) : formatWesternGrouping(rounded);
    const prefix = includeSymbol ? symbol : "";
    return isNegative ? `-${prefix}${grouped}` : `${prefix}${grouped}`;
  }

  // 3. Headline / Compact style:
  // For USD: rounded to nearest $1,000 per design.md section 8
  if (!isINR) {
    const roundedUSD = Math.round(absAmount / 1000) * 1000;
    const groupedUSD = formatWesternGrouping(roundedUSD);
    const prefix = includeSymbol ? symbol : "";
    return isNegative ? `-${prefix}${groupedUSD}` : `${prefix}${groupedUSD}`;
  }

  // For INR:
  // Convert to Lakhs Per Annum (LPA) if given in raw rupees
  const lpaValue = unit === "rupees" || unit === "raw" ? absAmount / 100000 : absAmount;

  // Crore transition threshold: >= 100 lakh (1 crore) per design.md section 8
  const isCrore = lpaValue >= 100.0;
  const numDecimals = decimals !== undefined ? decimals : 1;

  let displayNumStr: string;
  let unitSuffix = "";

  if (isCrore) {
    const croreValue = roundToPrecision(lpaValue / 100.0, numDecimals);
    displayNumStr = croreValue.toFixed(numDecimals);
    unitSuffix = includeUnit ? " crore" : "";
  } else {
    const roundedLpa = roundToPrecision(lpaValue, numDecimals);
    displayNumStr = roundedLpa.toFixed(numDecimals);
    unitSuffix = includeUnit ? " lakh" : "";
  }

  const prefix = includeSymbol ? symbol : "";
  const formatted = `${prefix}${displayNumStr}${unitSuffix}`;

  return isNegative ? `-${formatted}` : formatted;
}

/**
 * Format an estimated range: e.g. "₹12.5 to ₹18.0 lakh a year" or "$120,000 to $180,000 a year"
 * per design.md section 8 & 9.
 */
export function formatRange(
  p10: number | null | undefined,
  p90: number | null | undefined,
  options: MoneyFormatOptions = {}
): string {
  if (p10 === null || p10 === undefined || p90 === null || p90 === undefined || isNaN(p10) || isNaN(p90)) {
    return "—";
  }

  const { currency = "INR" } = options;
  const isINR = currency.toUpperCase() === "INR";

  if (isINR) {
    // End amounts formatted with symbol but without the word 'lakh' until the end of the clause
    const p10Str = formatMoney(p10, { ...options, includeUnit: false, style: "headline" });
    const p90Str = formatMoney(p90, { ...options, includeUnit: true, style: "headline" });
    return `${p10Str} to ${p90Str} a year`;
  } else {
    const p10Str = formatMoney(p10, { ...options, style: "headline" });
    const p90Str = formatMoney(p90, { ...options, style: "headline" });
    return `${p10Str} to ${p90Str} a year`;
  }
}
