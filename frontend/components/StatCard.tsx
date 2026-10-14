/** UI-UX.md: soft background, a big bold number and a small muted label. `note` sits under the number, smaller. */
export function StatCard({ value, label, note }: { value: string; label: string; note?: string }) {
  return (
    <div className="rounded-[22px] bg-soft p-[22px]">
      <b className="block text-[32px] font-bold leading-tight tabular-nums tracking-[-0.03em]">{value}</b>
      {note && <span className="block text-sm font-semibold text-ink">{note}</span>}
      <span className="block text-sm text-muted">{label}</span>
    </div>
  );
}
