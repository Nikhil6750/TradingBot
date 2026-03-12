import { Pause, Play, RotateCcw, SkipForward } from "lucide-react";

const SPEED_OPTIONS = [1, 2, 5, 10];

export default function ReplayControls({
    isPlaying,
    speed,
    cursor,
    totalCandles,
    canStep,
    onPlay,
    onPause,
    onStep,
    onReset,
    onSpeedChange,
    appearance = "default",
}) {
    const isMonochrome = appearance === "monochrome";

    return (
        <div
            className={`flex flex-col gap-4 rounded-2xl border px-5 py-4 shadow-[0_18px_50px_rgba(0,0,0,0.35)] ${
                isMonochrome ? "border-[#2a2a2a] bg-[#111111]" : "border-[#163246] bg-[#07131d]"
            }`}
        >
            <div className="flex flex-wrap items-center justify-between gap-4">
                <div className="flex items-center gap-2">
                    <button
                        type="button"
                        onClick={onPlay}
                        disabled={!canStep}
                        className={`flex items-center gap-2 rounded-xl border px-4 py-2 text-sm font-semibold transition disabled:cursor-not-allowed disabled:opacity-40 ${
                            isMonochrome
                                ? "border-white/15 bg-white/10 text-white hover:bg-white/15"
                                : "border-emerald-500/30 bg-emerald-500/15 text-emerald-300 hover:bg-emerald-500/25"
                        }`}
                    >
                        <Play size={16} />
                        Play
                    </button>
                    <button
                        type="button"
                        onClick={onPause}
                        disabled={!isPlaying}
                        className={`flex items-center gap-2 rounded-xl border border-white/10 bg-white/5 px-4 py-2 text-sm font-semibold transition hover:bg-white/10 disabled:cursor-not-allowed disabled:opacity-40 ${
                            isMonochrome ? "text-white" : "text-slate-200"
                        }`}
                    >
                        <Pause size={16} />
                        Pause
                    </button>
                    <button
                        type="button"
                        onClick={onStep}
                        disabled={!canStep}
                        className={`flex items-center gap-2 rounded-xl border px-4 py-2 text-sm font-semibold transition disabled:cursor-not-allowed disabled:opacity-40 ${
                            isMonochrome
                                ? "border-[#2a2a2a] bg-[#000000] text-white hover:bg-[#1a1a1a]"
                                : "border-sky-500/30 bg-sky-500/10 text-sky-200 hover:bg-sky-500/20"
                        }`}
                    >
                        <SkipForward size={16} />
                        Next Candle
                    </button>
                    <button
                        type="button"
                        onClick={onReset}
                        className={`flex items-center gap-2 rounded-xl border border-white/10 bg-white/5 px-3 py-2 text-sm font-semibold transition hover:bg-white/10 ${
                            isMonochrome ? "text-white/75" : "text-slate-300"
                        }`}
                    >
                        <RotateCcw size={15} />
                        Reset
                    </button>
                </div>

                <div className={`flex items-center gap-2 rounded-xl border p-1 ${isMonochrome ? "border-[#2a2a2a] bg-[#000000]" : "border-white/10 bg-[#0b1b28]"}`}>
                    {SPEED_OPTIONS.map((option) => (
                        <button
                            key={option}
                            type="button"
                            onClick={() => onSpeedChange(option)}
                            className={`rounded-lg px-3 py-1.5 text-xs font-bold transition ${
                                speed === option
                                    ? (isMonochrome ? "bg-white text-black" : "bg-[#d6f36e] text-[#0c1117]")
                                    : (isMonochrome ? "text-white/65 hover:bg-white/5 hover:text-white" : "text-slate-300 hover:bg-white/5 hover:text-white")
                            }`}
                        >
                            {option}x
                        </button>
                    ))}
                </div>
            </div>

            <div className="space-y-2">
                <div className={`flex items-center justify-between text-xs ${isMonochrome ? "text-white/48" : "text-slate-400"}`}>
                    <span>Replay progress</span>
                    <span>{Math.min(cursor + 1, totalCandles)} / {totalCandles}</span>
                </div>
                <div className="h-2 overflow-hidden rounded-full bg-white/5">
                    <div
                        className={`h-full rounded-full transition-[width] duration-150 ${isMonochrome ? "bg-white" : "bg-gradient-to-r from-emerald-400 via-lime-300 to-amber-300"}`}
                        style={{
                            width: totalCandles > 0 ? `${((cursor + 1) / totalCandles) * 100}%` : "0%",
                        }}
                    />
                </div>
            </div>
        </div>
    );
}
