import type { OrderItem } from "@/lib/api/types";

import { ProductImage } from "./ProductImage";

/**
 * A small square picture for an item in checkout or an order: its photo (for a custom request, the buyer's
 * first reference photo), or its category's line drawing on the tint when there's no photo.
 */
export function ItemThumb({
  name,
  image,
  tint,
  art,
  size = 56,
}: {
  name: string;
  image: string | null;
  tint: string;
  art: string;
  size?: number;
}) {
  return (
    <span className="block flex-none overflow-hidden rounded-[14px]" style={{ width: size, height: size }}>
      <ProductImage product={{ name, image, category: { tint, art } }} />
    </span>
  );
}

/** Convenience for order items, which carry their own picture fields. */
export function OrderItemThumb({ item, size }: { item: OrderItem; size?: number }) {
  return <ItemThumb name={item.name} image={item.image} tint={item.tint} art={item.art} size={size} />;
}
