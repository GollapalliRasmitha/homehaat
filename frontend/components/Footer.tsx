import Link from "next/link";

export function Footer() {
  return (
    <footer className="mt-20 border-t border-line py-10">
      <div className="wrap flex flex-wrap items-center justify-between gap-4">
        <span className="text-xl font-extrabold tracking-[-0.04em]">homehaat</span>
        <nav aria-label="Footer" className="flex flex-wrap gap-6 text-[15px]">
          <Link href="/sell" className="text-muted no-underline hover:text-ink">
            Sell on HomeHaat
          </Link>
          <Link href="/cart" className="text-muted no-underline hover:text-ink">
            Bag
          </Link>
          <Link href="/orders" className="text-muted no-underline hover:text-ink">
            My orders
          </Link>
          <Link href="/account" className="text-muted no-underline hover:text-ink">
            Account
          </Link>
        </nav>
      </div>
    </footer>
  );
}
