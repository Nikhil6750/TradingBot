export default function Topbar({ title, right = null }) {
  return (
    <div className="h-12 flex items-center justify-between px-3 border-b border-neutral-800 bg-[#111]">
      <div className="flex items-center gap-2">
        <div className="text-[14px] text-neutral-200">{title}</div>
        <span className="text-[10px] border border-neutral-800 px-2 py-[2px] rounded-full bg-[#151515]">
          MVP
        </span>
      </div>
      <div>{right}</div>
    </div>
  );
}
