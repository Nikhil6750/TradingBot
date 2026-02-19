// src/main.jsx
import React, { Suspense, lazy } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import App from "./App";
import ErrorBoundary from "./components/ErrorBoundary";
import "./index.css";   // Tailwind + custom styles

const StrategyBuilder = lazy(() => import("./pages/StrategyBuilder"));

const RouteNotFound = () => (
  <div style={{ padding: 24, color: "#e5e7eb" }}>
    <h2 style={{ fontSize: 18, marginBottom: 8 }}>Route not found</h2>
    <div style={{ fontSize: 13, color: "#94a3b8" }}>
      The requested page does not exist.
    </div>
  </div>
);

createRoot(document.getElementById("root")).render(
  <ErrorBoundary>
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<App />}>
          <Route
            index
            element={(
              <Suspense fallback={<div style={{ padding: 24, color: "#e5e7eb" }}>Loading...</div>}>
                <StrategyBuilder />
              </Suspense>
            )}
          />
          <Route path="*" element={<RouteNotFound />} />
        </Route>
      </Routes>
    </BrowserRouter>
  </ErrorBoundary>
);
