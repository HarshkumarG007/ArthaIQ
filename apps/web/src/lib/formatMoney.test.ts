import { describe, it, expect } from "vitest";
import {
  formatMoney,
  formatRange,
  formatIndianGrouping,
  formatWesternGrouping,
} from "./formatMoney";

describe("formatIndianGrouping", () => {
  it("formats standard numbers with 3,2,2 Indian grouping", () => {
    expect(formatIndianGrouping(0)).toBe("0");
    expect(formatIndianGrouping(5)).toBe("5");
    expect(formatIndianGrouping(50)).toBe("50");
    expect(formatIndianGrouping(500)).toBe("500");
    expect(formatIndianGrouping(1234)).toBe("1,234");
    expect(formatIndianGrouping(12345)).toBe("12,345");
    // Crucial check from design.md section 8: (1,23,456, not 123,456)
    expect(formatIndianGrouping(123456)).toBe("1,23,456");
    expect(formatIndianGrouping(1234567)).toBe("12,34,567");
    expect(formatIndianGrouping(10000000)).toBe("1,00,00,000"); // 1 crore
    expect(formatIndianGrouping(12345678)).toBe("1,23,45,678");
    expect(formatIndianGrouping(100000000)).toBe("10,00,00,000"); // 10 crore
  });

  it("handles decimal places cleanly", () => {
    expect(formatIndianGrouping("123456.75")).toBe("1,23,456.75");
    expect(formatIndianGrouping(12345.5)).toBe("12,345.5");
  });

  it("handles negative numbers and zero values", () => {
    expect(formatIndianGrouping(-123456)).toBe("-1,23,456");
    expect(formatIndianGrouping(-500)).toBe("-500");
    expect(formatIndianGrouping(0)).toBe("0");
    expect(formatIndianGrouping("")).toBe("0");
  });
});

describe("formatWesternGrouping", () => {
  it("formats numbers with standard 3,3 grouping for Western currencies", () => {
    expect(formatWesternGrouping(123456)).toBe("123,456");
    expect(formatWesternGrouping(1234567)).toBe("1,234,567");
    expect(formatWesternGrouping(-1234567)).toBe("-1,234,567");
  });
});

describe("formatMoney — INR (Indian Rupee)", () => {
  it("formats LPA to one decimal place in headline style", () => {
    expect(formatMoney(12.5)).toBe("₹12.5 lakh");
    expect(formatMoney(1.0)).toBe("₹1.0 lakh");
    expect(formatMoney(0.8)).toBe("₹0.8 lakh");
    expect(formatMoney(99.9)).toBe("₹99.9 lakh");
  });

  it("transitions to crore from 100 lakh per design.md section 8", () => {
    // Crore transition threshold: >= 100 lakh
    expect(formatMoney(100.0)).toBe("₹1.0 crore");
    expect(formatMoney(120.0)).toBe("₹1.2 crore");
    expect(formatMoney(250.0)).toBe("₹2.5 crore");
  });

  it("supports raw rupees unit input", () => {
    expect(formatMoney(1250000, { unit: "rupees" })).toBe("₹12.5 lakh");
    expect(formatMoney(10000000, { unit: "rupees" })).toBe("₹1.0 crore");
    expect(formatMoney(15000000, { unit: "rupees" })).toBe("₹1.5 crore");
  });

  it("supports table style with Indian digit grouping and no symbol by default", () => {
    expect(formatMoney(123456, { style: "table" })).toBe("1,23,456");
    expect(formatMoney(123456, { style: "table", includeSymbol: true })).toBe("₹1,23,456");
  });

  it("supports full style converting LPA to full Indian formatted rupees", () => {
    expect(formatMoney(12.5, { style: "full", unit: "lpa" })).toBe("₹12,50,000");
    expect(formatMoney(123456, { style: "full", unit: "rupees" })).toBe("₹1,23,456");
  });

  it("respects includeSymbol and includeUnit options", () => {
    expect(formatMoney(12.5, { includeSymbol: false })).toBe("12.5 lakh");
    expect(formatMoney(12.5, { includeUnit: false })).toBe("₹12.5");
    expect(formatMoney(12.5, { includeSymbol: false, includeUnit: false })).toBe("12.5");
  });

  it("handles negative amounts cleanly", () => {
    expect(formatMoney(-12.5)).toBe("-₹12.5 lakh");
    expect(formatMoney(-100.0)).toBe("-₹1.0 crore");
    expect(formatMoney(-123456, { style: "table" })).toBe("-1,23,456");
  });

  it("handles zero and invalid amounts without throwing", () => {
    expect(formatMoney(0)).toBe("₹0.0 lakh");
    expect(formatMoney(null)).toBe("—");
    expect(formatMoney(undefined)).toBe("—");
    expect(formatMoney(NaN)).toBe("—");
  });
});

describe("formatMoney — USD (US Dollar)", () => {
  it("rounds USD to nearest $1,000 per design.md section 8", () => {
    expect(formatMoney(125000, { currency: "USD" })).toBe("$125,000");
    expect(formatMoney(125400, { currency: "USD" })).toBe("$125,000");
    expect(formatMoney(125600, { currency: "USD" })).toBe("$126,000");
    expect(formatMoney(1000, { currency: "USD" })).toBe("$1,000");
  });

  it("supports table style for USD", () => {
    expect(formatMoney(123456, { currency: "USD", style: "table" })).toBe("123,456");
    expect(formatMoney(123456, { currency: "USD", style: "table", includeSymbol: true })).toBe("$123,456");
  });

  it("handles negative and zero USD amounts", () => {
    expect(formatMoney(0, { currency: "USD" })).toBe("$0");
    expect(formatMoney(-50000, { currency: "USD" })).toBe("-$50,000");
  });
});

describe("formatRange", () => {
  it("formats INR estimate range per design.md section 9 display line", () => {
    // "₹12.5 to ₹18.0 lakh a year"
    const range = formatRange(12.5, 18.0);
    expect(range).toBe("₹12.5 to ₹18.0 lakh a year");
  });

  it("formats USD estimate range per design.md section 9 display line", () => {
    // "$120,000 to $180,000 a year"
    const range = formatRange(120000, 180000, { currency: "USD" });
    expect(range).toBe("$120,000 to $180,000 a year");
  });

  it("returns fallback dash when either boundary is missing or invalid", () => {
    expect(formatRange(null, 18.0)).toBe("—");
    expect(formatRange(12.5, null)).toBe("—");
    expect(formatRange(NaN, 18.0)).toBe("—");
  });
});
