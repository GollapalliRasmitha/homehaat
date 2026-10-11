"use client";

import { StoreForm } from "@/components/StoreForm";
import { useSession } from "@/lib/session";
import { useSeller } from "@/lib/seller-context";

export default function StoreSettingsPage() {
  const { store, setStore } = useSeller();
  const { refresh } = useSession();
  return (
    <div className="mx-auto max-w-[720px]">
      <StoreForm
        store={store}
        onSaved={async (saved) => {
          setStore(saved); // the heading and "Paused" badge update at once
          await refresh(); // the shop link may have changed
        }}
      />
    </div>
  );
}
