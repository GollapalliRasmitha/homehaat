import { ArrowUpRight } from "lucide-react";
import Image from "next/image";
import Link from "next/link";

import { unsplash } from "@/lib/photos";

/** UI-UX.md showcase card: big photo (radius 28), white label card bottom-left, round arrow bottom-right. */
export function ShowcaseCard({
  href,
  title,
  subtitle,
  photoId,
  tint,
  priority = false,
}: {
  href: string;
  title: string;
  subtitle: string;
  photoId: string;
  tint: string;
  priority?: boolean;
}) {
  return (
    <Link
      href={href}
      className="group relative block aspect-[1.18] overflow-hidden rounded-[28px] no-underline"
      style={{ background: tint }}
    >
      <Image
        src={unsplash(photoId, 1000)}
        alt=""
        fill
        priority={priority}
        sizes="(max-width: 900px) 100vw, 33vw"
        className="object-cover transition-transform duration-[600ms] group-hover:scale-[1.04]"
      />
      <span className="absolute bottom-4 left-4 right-20 rounded-[18px] bg-white px-4 py-3">
        <b className="block text-xl font-bold tracking-[-0.03em]">{title}</b>
        <span className="text-[15px] text-muted">{subtitle}</span>
      </span>
      <span className="absolute bottom-4 right-4 flex size-[52px] items-center justify-center rounded-full bg-white" aria-hidden="true">
        <ArrowUpRight size={18} />
      </span>
    </Link>
  );
}
