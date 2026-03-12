/**
 * GlassPanel — borderless card with soft depth shadow.
 * Replaces the old bright-bordered glass aesthetic with a
 * modern fintech "floating panel" look.
 */
export default function GlassPanel({ children, className = "" }) {
    return (
        <div
            className={`bg-panel rounded-2xl transition-all duration-300 ${className}`}
            style={{ boxShadow: "0 10px 40px rgba(0,0,0,0.45)" }}
        >
            {children}
        </div>
    );
}
