/** UI-UX.md: soft background, a big bold number and a small muted label. `note` follows the number, smaller. */
export function StatCard({ value, label, note }: { value: string; label: string; note?: string }) {
  return (
    <div className="rounded-[22px] bg-soft p-[22px]">
      <b className="block text-[32px] font-bold tabular-nums tracking-[-0.03em]">
        {value}
        {note && <span className="text-base font-semibold tracking-normal text-muted"> · {note}</span>}
      </b>
      <span className="text-sm text-muted">{label}</span>
    </div>
  );
}
