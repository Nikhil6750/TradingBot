import { useTheme } from "../../context/ThemeContext";
import { Sun, Moon } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";

export default function ThemeToggle() {
    const { theme, toggleTheme } = useTheme();

    return (
        <motion.button
            onClick={toggleTheme}
            className="fixed top-6 right-6 z-50 p-2.5 rounded-full bg-surface/80 border border-border text-textSecondary hover:text-textPrimary hover:bg-panel shadow-sm hover:shadow-md cursor-pointer transition-colors duration-300"
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            style={{ backdropFilter: "blur(8px)" }}
        >
            <AnimatePresence mode="wait" initial={false}>
                <motion.div
                    key={theme}
                    initial={{ opacity: 0, rotate: -45, scale: 0.5 }}
                    animate={{ opacity: 1, rotate: 0, scale: 1 }}
                    exit={{ opacity: 0, rotate: 45, scale: 0.5 }}
                    transition={{ duration: 0.25, ease: "easeInOut" }}
                >
                    {theme === "dark" ? (
                        <Moon className="w-5 h-5" strokeWidth={1.8} />
                    ) : (
                        <Sun className="w-5 h-5" strokeWidth={1.8} />
                    )}
                </motion.div>
            </AnimatePresence>
        </motion.button>
    );
}
