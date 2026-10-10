/**
 * Fine black line drawings, one per category (UI-UX.md section 7).
 * Shown on the category tint when a product has no photo yet. Never a stock photo.
 * The markup below is fixed design artwork, not user input.
 */

const T = "rgba(17,17,17,.06)";

const DRAWINGS: Record<string, string> = {
  cake: `<path d="M14 100h92"/><path d="M28 64v30c0 4 14 7 32 7s32-3 32-7V64"/><ellipse cx="60" cy="64" rx="32" ry="7" fill="#fff"/><path d="M28 68c3 7 7 7 9 2 2 8 7 8 9 1 3 8 8 8 10 0 3 8 8 8 10 1 3 7 8 7 10-1 3 6 7 6 8-3" fill="none"/><path d="M28 84c0 4 14 7 32 7s32-3 32-7" fill="none" stroke-dasharray="2 4"/><rect x="57" y="42" width="6" height="18" rx="1" fill="${T}"/><path d="M60 28c4 4 5 8 0 11-5-3-4-7 0-11z" fill="#fff"/>`,
  jar: `<path d="M14 104h92"/><rect x="36" y="22" width="48" height="14" rx="3" fill="${T}"/><path d="M42 22v14M50 22v14M58 22v14M66 22v14M74 22v14" stroke-opacity=".35"/><path d="M34 40h52v52a10 10 0 0 1-10 10H44a10 10 0 0 1-10-10z" fill="#fff"/><rect x="43" y="56" width="34" height="24" rx="2" fill="#fff"/><path d="M49 64h22M52 71h16"/><path d="M40 46v40" stroke-opacity=".3"/>`,
  chakli: `<ellipse cx="60" cy="96" rx="46" ry="8" fill="#fff"/><ellipse cx="60" cy="96" rx="36" ry="5" fill="${T}" stroke="none"/><path d="M60 62a3 3 0 0 1 6 0a6 6 0 0 1-12 0a9 9 0 0 1 18 0a12 12 0 0 1-24 0a15 15 0 0 1 30 0a18 18 0 0 1-36 0a21 21 0 0 1 42 0a24 24 0 0 1-48 0" fill="none" stroke-width="2.2"/>`,
  frame: `<path d="M44 16l16-10 16 10"/><rect x="22" y="16" width="76" height="88" rx="2" fill="#fff"/><rect x="31" y="25" width="58" height="70" fill="${T}"/><path d="M33 86l16-18 10 10 8-7 20 15" fill="none"/><circle cx="73" cy="42" r="6" fill="#fff"/>`,
  spool: `<path d="M14 106h92"/><rect x="34" y="18" width="52" height="8" rx="3" fill="#fff"/><rect x="40" y="26" width="40" height="68" fill="${T}"/><path d="M40 34l40 6M40 44l40 6M40 54l40 6M40 64l40 6M40 74l40 6M40 84l40 6" stroke-opacity=".45"/><rect x="34" y="94" width="52" height="8" rx="3" fill="#fff"/><path d="M80 58c12 2 18 12 12 24s-2 18 8 20" fill="none"/><path d="M100 26l-6 56" /><ellipse cx="99.5" cy="31" rx="1.2" ry="3" fill="#fff"/>`,
  gift: `<path d="M14 104h92"/><rect x="26" y="56" width="68" height="46" rx="2" fill="#fff"/><rect x="22" y="44" width="76" height="14" rx="2" fill="${T}"/><path d="M56 44v58M64 44v58"/><path d="M60 44c-6-14-24-16-22-4 2 6 14 6 22 4zM60 44c6-14 24-16 22-4-2 6-14 6-22 4z" fill="#fff"/>`,
  ring: `<circle cx="60" cy="78" r="28" fill="none"/><circle cx="60" cy="78" r="23" fill="none" stroke-opacity=".4"/><path d="M48 38l6-8h12l6 8-12 14z" fill="#fff"/><path d="M48 38h24M54 30l6 8 6-8M60 52l-6-14M60 52l6-14" stroke-opacity=".6"/><path d="M84 26l3-3M88 34h4M36 26l-3-3" stroke-opacity=".5"/>`,
  pot: `<path d="M14 104h92"/><path d="M60 62V32"/><path d="M60 52c-14-2-22-12-20-22 12 2 20 10 20 22zM60 42c12-2 20-12 18-22-12 2-18 10-18 22z" fill="${T}"/><path d="M38 72h44l-6 32H44z" fill="#fff"/><rect x="34" y="62" width="52" height="10" rx="2" fill="#fff"/>`,
};

export function CategoryArt({ art, className }: { art: string; className?: string }) {
  return (
    <svg
      className={className}
      viewBox="0 0 120 120"
      fill="none"
      stroke="#111"
      strokeWidth={1.5}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      dangerouslySetInnerHTML={{ __html: DRAWINGS[art] ?? DRAWINGS.gift }}
    />
  );
}

/** The CSS variable for a category tint, e.g. "blush" -> "var(--blush)". */
export const tintVar = (tint: string) => `var(--${tint})`;
