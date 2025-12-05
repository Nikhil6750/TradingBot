// src/main.jsx
import { createRoot } from "react-dom/client";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import App from "./App";
import Chat from "./pages/Chat";
import Backtest from "./pages/Backtest";
import News from "./pages/News";
import CSVWindowChart from "./pages/CSVWindowChart";
import CSVPlotter from "./pages/CSVPlotter";
import "./index.css";   // Tailwind + custom styles

createRoot(document.getElementById("root")).render(
  <BrowserRouter>
    <Routes>
      <Route path="/" element={<App />}>
        <Route index element={<Chat />} />
        <Route path="chat" element={<Chat />} />
        <Route path="backtest" element={<Backtest />} />
        <Route path="news" element={<News />} />
        <Route path="csv-chart" element={<CSVWindowChart />} />
        <Route path="plot" element={<CSVPlotter />} />
      </Route>
    </Routes>
  </BrowserRouter>
);
