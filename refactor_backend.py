import os
import shutil
from pathlib import Path

def setup_structure():
    base = Path("backend")
    
    dirs = [
        "core", "database", "database/migrations", "auth", "strategies",
        "backtesting", "replay", "ml", "market_data", "api", "utils"
    ]
    
    for d in dirs:
        (base / d).mkdir(parents=True, exist_ok=True)
        (base / d / "__init__.py").touch(exist_ok=True)

    moves = {
        "config.py": "core/settings.py",
        "auth/security.py": "core/security.py",
        "auth/jwt_handler.py": "core/jwt.py",
        "database.py": "database/database.py",
        "models/user.py": "database/models.py",
        "auth/google_oauth.py": "auth/google_auth.py",
        "auth/otp.py": "auth/otp_auth.py",
        "auth/routes.py": "api/auth_routes.py",
        "backtesting/backtest_engine.py": "api/backtest_routes.py",
        "replay/replay_engine.py": "api/replay_routes.py",
        "metrics.py": "backtesting/metrics.py",
        "regime_detection.py": "ml/regime_detection.py",
        "data_loader.py": "market_data/loaders.py",
        "utils/helpers.py": "utils/helpers.py",
    }
    
    for src, dst in moves.items():
        src_path = base / src
        dst_path = base / dst
        if src_path.exists():
            shutil.move(str(src_path), str(dst_path))
            print(f"Moved {src} to {dst}")
        else:
            print(f"File {src} not found, skipping.")

    # Move logic out of api routes to engines if needed, or simply rename for now.
    # The prompt asked for `backtest_engine.py` in `backtesting/` and `backtest_routes.py` in `api/`.
    # Let's create dummy files for the rest of the requested layout.
    
    touch_files = [
        "core/oauth.py",
        "auth/routes.py",
        "auth/utils.py",
        "strategies/templates.py",
        "strategies/indicators.py",
        "backtesting/backtest_engine.py",
        "backtesting/execution.py",
        "replay/replay_engine.py",
        "replay/replay_api.py",
        "ml/prediction_models.py",
        "ml/feature_engineering.py",
        "market_data/csv_loader.py",
        "market_data/preprocessing.py",
        "api/strategy_routes.py",
        "utils/logger.py",
    ]
    
    for f in touch_files:
        (base / f).touch(exist_ok=True)

if __name__ == "__main__":
    setup_structure()
