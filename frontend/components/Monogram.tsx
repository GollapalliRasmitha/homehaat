/**
 * UI-UX.md maker monogram: a round badge in a dark tone with the shop's first letter in the italic serif.
 * The tone is picked from the shop link, so a shop always gets the same colour.
 */

const TONES = ["var(--mono-1)", "var(--mono-2)", "var(--mono-3)", "var(--mono-4)", "var(--mono-5)"];

export function toneFor(slug: string): string {
  let hash = 0;
  for (const char of slug) hash = (hash * 31 + char.charCodeAt(0)) >>> 0;
  return TONES[hash % TONES.length];
}

export function Monogram({ name, slug, size = 58 }: { name: string; slug: string; size?: number }) {
  return (
    <span
      aria-hidden="true"
      className="serif flex flex-none items-center justify-center rounded-full text-white"
      style={{ width: size, height: size, fontSize: size * 0.48, background: toneFor(slug) }}
    >
      {(name.trim()[0] ?? "?").toUpperCase()}
    </span>
  );
}
