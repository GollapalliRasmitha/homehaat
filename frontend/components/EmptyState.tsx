import Image from "next/image";

import { PHOTOS, unsplash } from "@/lib/photos";

/** UI-UX.md section 6: a soft panel, a round photo, a short heading, one line of help, one action. */
export function EmptyState({
  title,
  text,
  photoId = PHOTOS.crafts,
  action,
}: {
  title: string;
  text: string;
  photoId?: string;
  action?: React.ReactNode;
}) {
  return (
    <div className="flex flex-col items-center gap-3 rounded-[24px] bg-soft px-5 py-16 text-center">
      <Image
        src={unsplash(photoId, 300)}
        alt=""
        width={120}
        height={120}
        className="mb-1.5 size-[120px] rounded-full object-cover"
      />
      <h2 className="text-[24px]">{title}</h2>
      <p className="mb-1.5 max-w-[440px] text-muted">{text}</p>
      {action}
    </div>
  );
}
