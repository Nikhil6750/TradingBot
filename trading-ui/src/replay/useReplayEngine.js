import { useEffect, useRef, useState } from "react";

const SPEED_INTERVALS = {
    1: 1000,
    2: 500,
    5: 200,
    10: 100,
};

function clampCursor(candles, cursor) {
    if (!Array.isArray(candles) || candles.length === 0) {
        return 0;
    }

    return Math.max(0, Math.min(cursor, candles.length - 1));
}

export function useReplayEngine({
    candles = [],
    initialCursor = 0,
    initialSpeed = 1,
    onCandle,
    onReset,
}) {
    const [cursor, setCursor] = useState(() => clampCursor(candles, initialCursor));
    const [isPlaying, setIsPlaying] = useState(false);
    const [speed, setSpeed] = useState(initialSpeed);

    const previousCursorRef = useRef(clampCursor(candles, initialCursor));
    const onCandleRef = useRef(onCandle);
    const onResetRef = useRef(onReset);

    useEffect(() => {
        onCandleRef.current = onCandle;
    }, [onCandle]);

    useEffect(() => {
        onResetRef.current = onReset;
    }, [onReset]);

    useEffect(() => {
        const nextCursor = clampCursor(candles, initialCursor);
        previousCursorRef.current = nextCursor;
        setCursor(nextCursor);
        setIsPlaying(false);
        onResetRef.current?.(candles.slice(0, nextCursor + 1), nextCursor);
    }, [candles, initialCursor]);

    useEffect(() => {
        if (cursor <= previousCursorRef.current) {
            previousCursorRef.current = cursor;
            return;
        }

        for (let index = previousCursorRef.current + 1; index <= cursor; index += 1) {
            onCandleRef.current?.(candles[index], index);
        }

        previousCursorRef.current = cursor;
    }, [candles, cursor]);

    useEffect(() => {
        if (!isPlaying || candles.length === 0) {
            return undefined;
        }

        const interval = window.setInterval(() => {
            setCursor((currentCursor) => {
                const nextCursor = Math.min(currentCursor + 1, candles.length - 1);
                if (nextCursor === currentCursor) {
                    setIsPlaying(false);
                }
                return nextCursor;
            });
        }, SPEED_INTERVALS[speed] || SPEED_INTERVALS[1]);

        return () => window.clearInterval(interval);
    }, [candles.length, isPlaying, speed]);

    function play() {
        if (candles.length > 0 && cursor < candles.length - 1) {
            setIsPlaying(true);
        }
    }

    function pause() {
        setIsPlaying(false);
    }

    function step() {
        setIsPlaying(false);
        setCursor((currentCursor) => Math.min(currentCursor + 1, Math.max(candles.length - 1, 0)));
    }

    function reset(nextCursor = initialCursor) {
        const normalizedCursor = clampCursor(candles, nextCursor);
        previousCursorRef.current = normalizedCursor;
        setIsPlaying(false);
        setCursor(normalizedCursor);
        onResetRef.current?.(candles.slice(0, normalizedCursor + 1), normalizedCursor);
    }

    function seek(nextCursor, options = {}) {
        const normalizedCursor = clampCursor(candles, nextCursor);
        const shouldPlay = Boolean(options.autoplay) && normalizedCursor < candles.length - 1;

        previousCursorRef.current = normalizedCursor;
        setCursor(normalizedCursor);
        setIsPlaying(shouldPlay);
        onResetRef.current?.(candles.slice(0, normalizedCursor + 1), normalizedCursor);
    }

    return {
        cursor,
        isPlaying,
        speed,
        setSpeed,
        play,
        pause,
        step,
        reset,
        seek,
    };
}

export default useReplayEngine;
