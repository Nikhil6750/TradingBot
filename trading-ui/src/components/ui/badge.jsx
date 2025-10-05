export default function Badge({children,className=""}){
  return <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs border border-neutral-800 bg-neutral-800/60 ${className}`}>{children}</span>;
}
