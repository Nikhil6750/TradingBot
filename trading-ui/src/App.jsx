// src/App.jsx
import { Outlet } from "react-router-dom";

export default function App() {
  return (
    <div className="h-screen bg-neutral-950 text-neutral-200 font-sans">
      <Outlet />
    </div>
  );
}
