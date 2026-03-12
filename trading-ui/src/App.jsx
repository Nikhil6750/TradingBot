// src/App.jsx
import { BrowserRouter as Router, Routes, Route, Navigate, useLocation } from "react-router-dom";
import { AnimatePresence } from "framer-motion";
import { Toaster } from "react-hot-toast";

import Intro from "./pages/Intro";
import StrategyLab from "./pages/StrategyLab";
import UploadData from "./pages/UploadData";
import Results from "./pages/Results";
import Dashboard from "./pages/Dashboard";
import BacktestHistory from "./pages/BacktestHistory";
import Analytics from "./pages/Analytics";
import MarketReplay from "./pages/MarketReplay";
import SessionPage from "./pages/SessionPage";
import AppNav from "./components/ui/AppNav";
import { ThemeProvider } from "./context/ThemeContext";
import ThemeToggle from "./components/ui/ThemeToggle";

// Routes that use the persistent navigation sidebar
const NAV_ROUTES = ["/dashboard", "/setup", "/upload", "/results", "/backtests", "/analytics", "/replay"];

function AnimatedRoutes() {
  const location = useLocation();
  const showNav = NAV_ROUTES.some(r => location.pathname === r || location.pathname.startsWith("/backtests/"));

  return (
    <>
      {showNav && <AppNav />}
      <div style={showNav ? { marginLeft: "200px", minHeight: "100vh" } : {}}>
        <AnimatePresence mode="wait">
          <Routes location={location} key={location.pathname}>
            {/* Landing */}
            <Route path="/" element={<Intro />} />

            {/* App — with sidebar */}
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/setup" element={<StrategyLab />} />
            <Route path="/upload" element={<UploadData />} />
            <Route path="/results" element={<Results />} />
            <Route path="/backtests" element={<BacktestHistory />} />
            <Route path="/analytics" element={<Analytics />} />
            <Route path="/replay" element={<MarketReplay />} />

            {/* FXReplay-style session chart view */}
            <Route path="/session/:id" element={<SessionPage />} />

            {/* Catch-all */}
            <Route path="*" element={<Navigate to="/" />} />
          </Routes>
        </AnimatePresence>
      </div>
    </>
  );
}

function App() {
  return (
    <ThemeProvider>
      <ThemeToggle />
      <Router>
        <Toaster position="top-right" toastOptions={{ style: { background: "#111", color: "#E5E5E5", border: "1px solid rgba(255,255,255,0.08)" } }} />
        <AnimatedRoutes />
      </Router>
    </ThemeProvider>
  );
}

export default App;
