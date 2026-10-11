"use client";

import { ArrowLeft, ArrowRight, ImagePlus, X } from "lucide-react";
import { useId, useRef, useState } from "react";
import { toast } from "sonner";

import { compressImage } from "@/lib/compress-image";

/** A photo in the picker: already saved (id + url) or new (blob, shown from a local preview url). */
export interface PickedPhoto {
  key: string;
  url: string;
  id?: number; // set for photos already saved on the server
  blob?: Blob; // set for new photos, uploaded when the form is saved
}

let nextKey = 0;

/**
 * Up to `max` photos. Drop files on it or browse; photos are shrunk in the browser first.
 * Reorder by dragging, or with the arrow buttons (works by keyboard too). The first photo is the main one.
 */
export function PhotoPicker({
  photos,
  onChange,
  max = 5,
  label = "Photos",
}: {
  photos: PickedPhoto[];
  onChange: (photos: PickedPhoto[]) => void;
  max?: number;
  label?: string;
}) {
  const inputId = useId();
  const input = useRef<HTMLInputElement>(null);
  const [dragOver, setDragOver] = useState(false);
  const [busy, setBusy] = useState(false);
  const dragFrom = useRef<number | null>(null);

  async function addFiles(files: FileList | File[]) {
    const room = max - photos.length;
    const chosen = Array.from(files).slice(0, room);
    if (files.length > room) toast(`Up to ${max} photos. ${room > 0 ? `Added the first ${room}.` : ""}`);
    if (!chosen.length) return;
    setBusy(true);
    const added: PickedPhoto[] = [];
    for (const file of chosen) {
      try {
        const blob = await compressImage(file);
        added.push({ key: `new-${nextKey++}`, url: URL.createObjectURL(blob), blob });
      } catch {
        toast(`Couldn't read ${file.name}. Please use a JPEG, PNG or WebP photo.`);
      }
    }
    setBusy(false);
    onChange([...photos, ...added]);
  }

  function move(from: number, to: number) {
    if (to < 0 || to >= photos.length || from === to) return;
    const next = [...photos];
    const [photo] = next.splice(from, 1);
    next.splice(to, 0, photo);
    onChange(next);
  }

  function remove(index: number) {
    const photo = photos[index];
    if (photo.blob) URL.revokeObjectURL(photo.url); // free the local preview
    onChange(photos.filter((_, i) => i !== index));
  }

  return (
    <div>
      <span className="field-label" id={`${inputId}-label`}>
        {max > 1 ? `${label} (up to ${max})` : label}
      </span>
      <div
        className={`flex flex-wrap items-center gap-3 rounded-[18px] border-[1.5px] border-dashed p-[18px] ${
          dragOver ? "border-ink bg-white" : "border-[#d6d6d6] bg-soft"
        }`}
        onDragOver={(e) => {
          if (e.dataTransfer.types.includes("Files")) {
            e.preventDefault();
            setDragOver(true);
          }
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={(e) => {
          if (!e.dataTransfer.files.length) return;
          e.preventDefault();
          setDragOver(false);
          addFiles(e.dataTransfer.files);
        }}
        aria-labelledby={`${inputId}-label`}
      >
        {photos.map((photo, i) => (
          <figure
            key={photo.key}
            className="relative m-0"
            draggable={max > 1}
            onDragStart={() => (dragFrom.current = i)}
            onDragOver={(e) => e.preventDefault()}
            onDrop={(e) => {
              if (dragFrom.current === null) return;
              e.preventDefault();
              e.stopPropagation();
              move(dragFrom.current, i);
              dragFrom.current = null;
            }}
          >
            <div className="relative">
              {/* Local previews are blob: URLs, which next/image can't optimise. */}
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={photo.url}
                alt={max > 1 ? `Photo ${i + 1}${i === 0 ? " (main photo)" : ""}` : "Chosen photo"}
                className={`size-[88px] rounded-[14px] object-cover ${max > 1 ? "cursor-grab" : ""}`}
              />
              {max > 1 && i === 0 && (
                <figcaption className="absolute bottom-1 left-1 rounded-full bg-white px-2 py-0.5 text-[11px] font-semibold">
                  Main
                </figcaption>
              )}
              <button
                type="button"
                onClick={() => remove(i)}
                aria-label={max > 1 ? `Remove photo ${i + 1}` : "Remove photo"}
                className="absolute -right-2 -top-2 flex size-7 items-center justify-center rounded-full border border-line bg-white hover:border-ink"
              >
                <X size={14} aria-hidden="true" />
              </button>
            </div>
            {max > 1 && (
              <div className="mt-1 flex justify-center gap-1">
                <button
                  type="button"
                  onClick={() => move(i, i - 1)}
                  disabled={i === 0}
                  aria-label={`Move photo ${i + 1} left`}
                  className="flex size-7 items-center justify-center rounded-full hover:bg-white disabled:opacity-30"
                >
                  <ArrowLeft size={14} aria-hidden="true" />
                </button>
                <button
                  type="button"
                  onClick={() => move(i, i + 1)}
                  disabled={i === photos.length - 1}
                  aria-label={`Move photo ${i + 1} right`}
                  className="flex size-7 items-center justify-center rounded-full hover:bg-white disabled:opacity-30"
                >
                  <ArrowRight size={14} aria-hidden="true" />
                </button>
              </div>
            )}
          </figure>
        ))}

        {photos.length < max && (
          <>
            <button type="button" className="btn btn-white" onClick={() => input.current?.click()} disabled={busy}>
              <ImagePlus size={18} aria-hidden="true" />
              {busy ? "Preparing photo…" : max > 1 ? "Add photos" : "Add photo"}
            </button>
            <input
              ref={input}
              id={inputId}
              type="file"
              accept="image/jpeg,image/png,image/webp"
              multiple={max > 1}
              className="sr-only"
              tabIndex={-1}
              onChange={(e) => {
                if (e.target.files) addFiles(e.target.files);
                e.target.value = ""; // so the same file can be picked again
              }}
            />
          </>
        )}
        <span className="basis-full text-[13px] text-muted">
          {max > 1
            ? "Drop photos here or use Add photos. A clear photo on a plain background works best. The first photo is the one buyers see first."
            : "Drop a photo here or use Add photo. A wide photo works best."}
        </span>
      </div>
    </div>
  );
}
