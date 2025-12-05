export default function Button({ className="", variant="solid", ...props }) {
  const base = "h-10 px-4 rounded-xl text-sm transition";
  const styles = {
    solid: "bg-emerald-500 text-white hover:brightness-110",
    ghost: "border border-neutral-800 text-neutral-200 hover:bg-neutral-900",
  };
  return <button className={`${base} ${styles[variant]} ${className}`} {...props} />;
}
