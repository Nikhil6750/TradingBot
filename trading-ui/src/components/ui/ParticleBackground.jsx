import { useCallback } from "react";
import Particles from "@tsparticles/react";
import { loadSlim } from "@tsparticles/slim";

/**
 * Premium financial-node particle background.
 * - Tiny circular "data" dots with subtle node links
 * - Very low opacity — purely atmospheric
 * - Gentle drift — never distracting
 */
export default function ParticleBackground() {
    const particlesInit = useCallback(async (engine) => {
        await loadSlim(engine);
    }, []);

    return (
        <Particles
            id="tsparticles"
            init={particlesInit}
            options={{
                background: { color: { value: "transparent" } },
                fpsLimit: 60,
                interactivity: {
                    events: {
                        onHover: { enable: true, mode: "grab" },
                        resize: true,
                    },
                    modes: {
                        grab: { distance: 160, links: { opacity: 0.15 } },
                    },
                },
                particles: {
                    color: { value: "#ffffff" },
                    links: {
                        color: "#ffffff",
                        distance: 140,
                        enable: true,
                        opacity: 0.06,
                        width: 0.8,
                    },
                    move: {
                        direction: "none",
                        enable: true,
                        outModes: { default: "bounce" },
                        random: true,
                        speed: 0.35,
                        straight: false,
                        attract: { enable: false },
                    },
                    number: {
                        density: { enable: true, area: 900 },
                        value: 55,
                    },
                    opacity: {
                        value: { min: 0.04, max: 0.18 },
                        animation: {
                            enable: true,
                            speed: 0.4,
                            sync: false,
                        },
                    },
                    shape: { type: "circle" },
                    size: {
                        value: { min: 1, max: 2.5 },
                        animation: {
                            enable: true,
                            speed: 0.8,
                            sync: false,
                        },
                    },
                },
                detectRetina: true,
            }}
            className="absolute inset-0 z-0 pointer-events-none"
        />
    );
}
