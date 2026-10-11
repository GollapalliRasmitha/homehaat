"use client";

import Image, { type ImageProps } from "next/image";
import { useCallback, useState } from "react";

/**
 * Images that never show a broken-image icon. If loading fails (offline, a slow photo
 * service, a missing upload), the image is removed and whatever is behind it shows
 * instead: the soft tint colour of its box, or the `fallback` (e.g. a category drawing).
 */

/**
 * Pages arrive as HTML from the server, so the browser may try (and fail) an image BEFORE
 * React is running and listening for onError. This ref callback catches that case: when the
 * image is attached, "already finished loading but has no pixels" means it already failed.
 */
function useFailed() {
  const [failed, setFailed] = useState(false);
  const ref = useCallback((img: HTMLImageElement | null) => {
    if (img && img.complete && img.naturalWidth === 0) setFailed(true);
  }, []);
  return { failed, ref, onError: () => setFailed(true) };
}

/** For Unsplash photos (category, showcase, cover fallback, empty states), via next/image. */
export function SafeImage({ fallback = null, ...props }: ImageProps & { fallback?: React.ReactNode }) {
  const { failed, ref, onError } = useFailed();
  if (failed) return <>{fallback}</>;
  return <Image {...props} alt={props.alt} ref={ref} onError={onError} />;
}

/** For seller uploads served by Django (/media/…), which don't go through next/image yet. */
export function SafeImg({
  fallback = null,
  alt,
  ...props
}: React.ImgHTMLAttributes<HTMLImageElement> & { alt: string; fallback?: React.ReactNode }) {
  const { failed, ref, onError } = useFailed();
  if (failed || !props.src) return <>{fallback}</>;
  // eslint-disable-next-line @next/next/no-img-element
  return <img {...props} alt={alt} ref={ref} onError={onError} />;
}
