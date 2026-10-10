import { apiFetch } from "./client";
import type { Category, Product } from "./types";

export const listCategories = () => apiFetch<Category[]>("/categories/");

export const listProducts = () => apiFetch<Product[]>("/products/");

export const getProduct = (id: number | string) => apiFetch<Product>(`/products/${id}/`);
