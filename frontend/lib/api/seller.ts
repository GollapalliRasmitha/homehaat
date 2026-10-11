import { apiFetch } from "./client";
import type {
  IncomingOrder,
  ProductPhoto,
  SellerOrderStatus,
  SellerOverview,
  SellerProduct,
  SellerReviews,
  Store,
} from "./types";

// --- the shop ---

export type StoreFields = Pick<
  Store,
  "name" | "kind" | "main_category" | "bio" | "area" | "delivery_days" | "delivery_fee_paise"
> & { slug?: string; is_active?: boolean };

export const getMyStore = () => apiFetch<Store>("/seller/store/");

export const openStore = (body: StoreFields) => apiFetch<Store>("/seller/store/", { method: "POST", body });

export const updateStore = (body: Partial<StoreFields>) =>
  apiFetch<Store>("/seller/store/", { method: "PATCH", body });

export function uploadCover(photo: Blob) {
  const form = new FormData();
  form.append("image", photo, "cover.jpg");
  return apiFetch<Store>("/seller/store/cover/", { method: "POST", form });
}

export const removeCover = () => apiFetch<Store>("/seller/store/cover/", { method: "DELETE" });

// --- dashboard ---

export const getOverview = () => apiFetch<SellerOverview>("/seller/overview/");

export const listIncomingOrders = (status?: SellerOrderStatus) =>
  apiFetch<IncomingOrder[]>(`/seller/orders/${status ? `?status=${status}` : ""}`);

/** Move an order to its next step (or "cancelled"). The server checks the move is allowed. */
export const changeOrderStatus = (id: number, status: SellerOrderStatus) =>
  apiFetch<IncomingOrder>(`/seller/orders/${id}/status/`, { method: "POST", body: { status } });

export const getMyReviews = () => apiFetch<SellerReviews>("/seller/reviews/");

// --- products ---

export type ProductFields = Pick<SellerProduct, "name" | "description" | "category" | "price_paise" | "stock">;

export const listMyProducts = () => apiFetch<SellerProduct[]>("/seller/products/");

export const getMyProduct = (id: number | string) => apiFetch<SellerProduct>(`/seller/products/${id}/`);

export const addProduct = (body: ProductFields) =>
  apiFetch<SellerProduct>("/seller/products/", { method: "POST", body });

export const updateProduct = (id: number, body: Partial<ProductFields & { is_active: boolean }>) =>
  apiFetch<SellerProduct>(`/seller/products/${id}/`, { method: "PATCH", body });

export function uploadProductPhoto(productId: number, photo: Blob) {
  const form = new FormData();
  form.append("image", photo, "photo.jpg");
  return apiFetch<ProductPhoto>(`/seller/products/${productId}/images/`, { method: "POST", form });
}

export const deleteProductPhoto = (productId: number, photoId: number) =>
  apiFetch<void>(`/seller/products/${productId}/images/${photoId}/`, { method: "DELETE" });

export const orderProductPhotos = (productId: number, ids: number[]) =>
  apiFetch<ProductPhoto[]>(`/seller/products/${productId}/images/order/`, { method: "POST", body: { ids } });
