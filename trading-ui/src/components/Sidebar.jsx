// src/components/Sidebar.jsx
import { NavLink } from "react-router-dom";

export default function Sidebar() {
  const links = [
    { name: "Strategy Builder", path: "/" },
  ];

  return (
    <div className="w-56 bg-neutral-900 p-4 flex flex-col gap-4">
      <h1 className="text-xl font-bold mb-6">Trading Bot</h1>
      <nav className="flex flex-col gap-2">
        {links.map((l) => (
          <NavLink
            key={l.path}
            to={l.path}
            className={({ isActive }) =>
              `px-3 py-2 rounded hover:bg-neutral-800 ${isActive ? "bg-neutral-800 font-semibold" : "text-neutral-400"
              }`
            }
          >
            {l.name}
          </NavLink>
        ))}
      </nav>
    </div>
  );
}
