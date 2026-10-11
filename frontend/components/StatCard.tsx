/** UI-UX.md: soft background, a big bold number and a small muted label. */
export function StatCard({ value, label }: { value: string; label: string }) {
  return (
    <div className="rounded-[22px] bg-soft p-[22px]">
      <b className="block text-[32px] font-bold tabular-nums tracking-[-0.03em]">{value}</b>
      <span className="text-sm text-muted">{label}</span>
    </div>
  );
}
