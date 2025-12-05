export default function Select({ children, ...props }){
  return <select {...props} className="h-10 px-3 rounded-xl bg-neutral-900 border border-neutral-800 text-sm outline-none focus:ring-1 focus:ring-emerald-400/40">{children}</select>;
}
