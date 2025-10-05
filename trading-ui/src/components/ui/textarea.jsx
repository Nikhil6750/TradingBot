export default function Textarea(props){
  return <textarea {...props} className={`h-24 px-3 py-2 rounded-xl bg-neutral-900 border border-neutral-800 text-sm outline-none resize-none focus:ring-1 focus:ring-emerald-400/40 ${props.className||""}`} />;
}
