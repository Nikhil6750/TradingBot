import os
import re

IMPORT_MAPPINGS = {
    r"from\s+backend\.config\s+import": r"from backend.core.settings import",
    r"import\s+backend\.config": r"import backend.core.settings",
    
    r"from\s+backend\.auth\.security\s+import": r"from backend.core.security import",
    r"import\s+backend\.auth\.security": r"import backend.core.security",
    
    r"from\s+backend\.auth\.jwt_handler\s+import": r"from backend.core.jwt import",
    r"import\s+backend\.auth\.jwt_handler": r"import backend.core.jwt",

    r"from\s+backend\.database\s+import": r"from backend.database.database import",
    r"import\s+backend\.database": r"import backend.database.database",

    r"from\s+backend\.models\.user\s+import": r"from backend.database.models import",
    r"import\s+backend\.models\.user": r"import backend.database.models",

    r"from\s+backend\.models(\s+)": r"from backend.database.models\1",

    r"from\s+backend\.auth\.google_oauth\s+import": r"from backend.auth.google_auth import",
    r"from\s+backend\.auth\.otp\s+import": r"from backend.auth.otp_auth import",
    r"from\s+backend\.auth\.routes\s+import": r"from backend.api.auth_routes import",
    
    r"from\s+backend\.backtesting\.backtest_engine\s+import": r"from backend.api.backtest_routes import",
    r"from\s+backend\.replay\.replay_engine\s+import": r"from backend.api.replay_routes import",
    
    r"from\s+backend\.metrics\s+import": r"from backend.backtesting.metrics import",
    r"from\s+backend\.regime_detection\s+import": r"from backend.ml.regime_detection import",
    r"from\s+backend\.data_loader\s+import": r"from backend.market_data.loaders import",
}

def rewrite_imports(directory):
    for root, _, files in os.walk(directory):
        if "venv" in root or "__pycache__" in root:
            continue
        for f in files:
            if not f.endswith(".py"):
                continue
            path = os.path.join(root, f)
            with open(path, "r", encoding="utf-8") as file:
                content = file.read()
            
            new_content = content
            for pattern, replacement in IMPORT_MAPPINGS.items():
                new_content = re.sub(pattern, replacement, new_content)
                
            if new_content != content:
                with open(path, "w", encoding="utf-8") as file:
                    file.write(new_content)
                print(f"Updated imports in {path}")

if __name__ == "__main__":
    rewrite_imports("backend")
