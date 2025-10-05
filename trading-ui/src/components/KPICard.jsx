export default function KPICard({ label, value }) {
  return (
    <div className="rounded-xl bg-neutral-900 border border-neutral-800 p-3">
      <div className="text-xs text-neutral-400">{label}</div>
      <div className="text-lg font-semibold">{String(value ?? "—")}</div>
    </div>
  );
}
