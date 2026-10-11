import Link from "next/link";

import { CategoryGrid } from "@/components/CategoryTile";
import { EmptyState } from "@/components/EmptyState";
import { listCategories } from "@/lib/api/catalog";
import { errorMessage } from "@/lib/api/client";
import type { Category } from "@/lib/api/types";

export default async function CategoriesPage() {
  let categories: Category[] | null = null;
  let loadError: unknown = null;
  try {
    categories = await listCategories(); // includes live product counts
  } catch (error) {
    loadError = error;
  }

  return (
    <>
      <div className="mb-4 text-sm text-muted">
        <Link href="/" className="text-muted">
          Home
        </Link>{" "}
        / Categories
      </div>
      <h1 className="title mb-7">
        All <span className="serif">categories</span>
      </h1>
      {categories ? (
        <CategoryGrid categories={categories} showCount />
      ) : (
        <EmptyState title="Couldn't load categories" text={errorMessage(loadError)} />
      )}
    </>
  );
}
