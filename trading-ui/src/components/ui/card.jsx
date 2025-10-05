export default function Card({ className="", children }) {
  return <div className={`rounded-2xl border border-neutral-800 bg-neutral-900 p-3 ${className}`}>{children}</div>;
}
