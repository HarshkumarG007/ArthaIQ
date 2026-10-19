import React, { useState, useRef, useEffect, useId } from "react";

export interface DefinitionPopoverProps {
  term: string;
  definition: string;
  glossaryUrl?: string;
  children?: React.ReactNode;
  className?: string;
}

/**
 * DefinitionPopover — Accessible progressive disclosure definition widget.
 * Per design.md section 8:
 * "A term with a dotted underline that opens a popover on click, tap or Enter.
 * Short definition plus a glossary link. Focus moves in and returns on Esc.
 * Essential definitions are never hover-only."
 */
export function DefinitionPopover({
  term,
  definition,
  glossaryUrl = "#glossary",
  children,
  className = "",
}: DefinitionPopoverProps): React.JSX.Element {
  const [isOpen, setIsOpen] = useState<boolean>(false);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const popoverRef = useRef<HTMLDivElement>(null);
  const popoverId = useId();

  // Close on Escape and return focus to trigger
  useEffect(() => {
    if (!isOpen) return;

    const handleKeyDown = (e: KeyboardEvent): void => {
      if (e.key === "Escape") {
        e.preventDefault();
        setIsOpen(false);
        triggerRef.current?.focus();
      }
    };

    const handleClickOutside = (e: MouseEvent): void => {
      if (
        popoverRef.current &&
        !popoverRef.current.contains(e.target as Node) &&
        triggerRef.current &&
        !triggerRef.current.contains(e.target as Node)
      ) {
        setIsOpen(false);
      }
    };

    document.addEventListener("keydown", handleKeyDown);
    document.addEventListener("mousedown", handleClickOutside);

    return () => {
      document.removeEventListener("keydown", handleKeyDown);
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, [isOpen]);

  const togglePopover = (): void => {
    setIsOpen((prev) => !prev);
  };

  return (
    <span className={`relative inline-block ${className}`}>
      <button
        ref={triggerRef}
        type="button"
        onClick={togglePopover}
        aria-expanded={isOpen}
        aria-controls={popoverId}
        aria-haspopup="dialog"
        className="inline-flex items-center text-inherit font-inherit border-b border-dotted border-ink-2 hover:border-ink focus:outline-none focus:ring-2 focus:ring-focus rounded-sm transition-colors cursor-pointer"
      >
        {children || term}
      </button>

      {isOpen && (
        <div
          ref={popoverRef}
          id={popoverId}
          role="dialog"
          aria-modal="false"
          aria-label={`Definition of ${term}`}
          data-testid="definition-popover"
          className="absolute left-0 bottom-full mb-2 z-30 w-72 p-3 bg-sheet border border-rule-strong rounded-control shadow-md text-left text-xs font-sans text-ink focus:outline-none animate-in fade-in zoom-in-95 duration-100"
        >
          <div className="flex items-start justify-between gap-2 border-b border-rule pb-1.5 mb-2">
            <span className="font-semibold text-ink">{term}</span>
            <button
              type="button"
              onClick={() => {
                setIsOpen(false);
                triggerRef.current?.focus();
              }}
              aria-label="Close definition"
              className="text-ink-3 hover:text-ink p-0.5 rounded focus:outline-none focus:ring-1 focus:ring-focus"
            >
              <svg className="w-3.5 h-3.5" viewBox="0 0 20 20" fill="currentColor">
                <path
                  fillRule="evenodd"
                  d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z"
                  clipRule="evenodd"
                />
              </svg>
            </button>
          </div>

          <p className="text-ink-2 leading-relaxed mb-2.5">{definition}</p>

          {glossaryUrl && (
            <a
              href={glossaryUrl}
              className="text-span hover:underline font-medium inline-flex items-center gap-1"
            >
              Learn more in methodology glossary &rarr;
            </a>
          )}
        </div>
      )}
    </span>
  );
}

export default DefinitionPopover;
