import Link from "next/link";

const LINKS = [
  { href: "/sell", label: "Sell on HomeHaat" },
  { href: "/custom", label: "Custom orders" },
  { href: "/orders", label: "My orders" },
  { href: "/account", label: "Account" },
];

export function Footer() {
  return (
    <footer className="mt-20 border-t border-line py-10">
      <div className="wrap flex flex-wrap items-center justify-between gap-4">
        <span className="text-xl font-extrabold tracking-[-0.04em]">homehaat</span>
        <nav aria-label="Footer" className="flex flex-wrap items-center gap-x-6 gap-y-2 text-[15px]">
          {LINKS.map((link) => (
            <Link key={link.href} href={link.href} className="text-muted no-underline hover:text-ink">
              {link.label}
            </Link>
          ))}
          {/* Category, showcase and empty-state photos are from Unsplash (free licence). */}
          <span className="text-[13px] text-muted">Photos: Unsplash</span>
        </nav>
      </div>
    </footer>
  );
}
