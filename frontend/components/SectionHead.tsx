import Link from "next/link";

/** Section heading with one italic serif accent ("Fresh *this week*") and an optional link on the right. */
export function SectionHead({
  title,
  accent,
  link,
  id,
}: {
  title: string;
  accent?: string;
  link?: { href: string; label: string };
  id?: string;
}) {
  return (
    <div className="mb-7 flex flex-wrap items-end justify-between gap-3">
      <h2 id={id} className="text-[clamp(30px,3.6vw,46px)] leading-[1.05]">
        {title} {accent && <span className="serif text-[1.08em]">{accent}</span>}
      </h2>
      {link && (
        <Link href={link.href} className="text-base font-medium underline-offset-4">
          {link.label}
        </Link>
      )}
    </div>
  );
}
