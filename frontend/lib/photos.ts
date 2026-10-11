/** Unsplash photo URL (free licence). Used only for category, banner and empty-state photos, never products. */
export const unsplash = (photoId: string, width = 800) =>
  `https://images.unsplash.com/photo-${photoId}?w=${width}&q=70&auto=format&fit=crop`;

// The same Unsplash photos as the categories (backend seed_categories), for showcase, banner and empty states.
export const PHOTOS = {
  cakes: "1588195538326-c5b1e9f80a1b",
  pickles: "1618150615391-6d1acab1e561",
  art: "1638430323177-8cb2d1febb0c",
  crafts: "1707944145479-12755f0434d8",
};
