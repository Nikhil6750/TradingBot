import os
import shutil
import re
from pathlib import Path

def refactor_frontend():
    base = Path("trading-ui/src")
    
    (base / "components/charts").mkdir(parents=True, exist_ok=True)
    (base / "components/auth").mkdir(parents=True, exist_ok=True)

    moves = {
        "components/ChartView.jsx": "components/charts/ChartView.jsx",
        "components/DurationHistogram.jsx": "components/charts/DurationHistogram.jsx",
        "components/EquityChart.jsx": "components/charts/EquityChart.jsx",
        "components/ForexChart.jsx": "components/charts/ForexChart.jsx",
        "components/MonthlyReturnsHeatmap.jsx": "components/charts/MonthlyReturnsHeatmap.jsx",
        "components/PnLHistogram.jsx": "components/charts/PnLHistogram.jsx",
        "components/SetupDetailChart.jsx": "components/charts/SetupDetailChart.jsx",
        "components/WinLossPie.jsx": "components/charts/WinLossPie.jsx",
        "components/ProtectedRoute.jsx": "components/auth/ProtectedRoute.jsx",
    }
    
    for src, dst in moves.items():
        src_path = base / src
        dst_path = base / dst
        if src_path.exists():
            shutil.move(str(src_path), str(dst_path))
            print(f"Moved {src} to {dst}")

    # For JSX relative import patching
    chart_components = [
        "ChartView", "DurationHistogram", "EquityChart", "ForexChart", 
        "MonthlyReturnsHeatmap", "PnLHistogram", "SetupDetailChart", "WinLossPie"
    ]
    auth_components = ["ProtectedRoute"]
    
    # We will just do a simple string replace for occurrences.
    # In pages (like `../components/EquityChart`), replace with `../components/charts/EquityChart`
    # In components (like `./EquityChart`), replace with `./charts/EquityChart`
    
    for root, _, files in os.walk(base):
        for f in files:
            if not f.endswith(('.jsx', '.js')):
                continue
                
            path = Path(root) / f
            with open(path, "r", encoding="utf-8") as file:
                content = file.read()
                
            new_content = content
            
            # Simple global string substitution
            for c in chart_components:
                new_content = new_content.replace(f"../components/{c}", f"../components/charts/{c}")
                if "components/charts" not in path.parts:
                    new_content = new_content.replace(f"./{c}", f"./charts/{c}")
                else:
                    new_content = new_content.replace(f"../{c}", f"./{c}")
                    
            for c in auth_components:
                new_content = new_content.replace(f"../components/{c}", f"../components/auth/{c}")
                if "components/auth" not in path.parts:
                    new_content = new_content.replace(f"./{c}", f"./auth/{c}")
                else:
                    new_content = new_content.replace(f"../{c}", f"./{c}")
                    
            if new_content != content:
                with open(path, "w", encoding="utf-8") as file:
                    file.write(new_content)
                print(f"Patched imports in {path}")

if __name__ == "__main__":
    refactor_frontend()
