/**
 * Shrinks a photo in the browser before upload, so a 6 MB phone photo becomes
 * ~300 KB: faster on mobile data, and well under the server's 5 MB limit.
 * The server still checks and cleans every photo (catalog/images.py).
 */

export const MAX_SIDE = 1600;

/** New width and height that fit inside max x max, keeping the shape. Never enlarges. */
export function fitWithin(width: number, height: number, max = MAX_SIDE): { width: number; height: number } {
  const scale = Math.min(1, max / Math.max(width, height));
  return { width: Math.round(width * scale), height: Math.round(height * scale) };
}

export async function compressImage(file: File, quality = 0.82): Promise<Blob> {
  if (!file.type.startsWith("image/")) throw new Error("Please choose a photo (JPEG, PNG or WebP).");
  // imageOrientation: "from-image" turns phone photos upright before we redraw them.
  const bitmap = await createImageBitmap(file, { imageOrientation: "from-image" });
  const { width, height } = fitWithin(bitmap.width, bitmap.height);
  const canvas = document.createElement("canvas");
  canvas.width = width;
  canvas.height = height;
  const context = canvas.getContext("2d")!;
  context.fillStyle = "#fff"; // transparent PNGs get a white background in JPEG
  context.fillRect(0, 0, width, height);
  context.drawImage(bitmap, 0, 0, width, height);
  bitmap.close();
  return new Promise((resolve, reject) =>
    canvas.toBlob((blob) => (blob ? resolve(blob) : reject(new Error("Couldn't read that photo."))), "image/jpeg", quality),
  );
}
