# inspect_hours.py
import glob
import pandas as pd
from helpers import get_env_float, get_env_str, parse_session, utc_to_local

SESSION_RAW     = get_env_str("SESSION", "ALL")
TZ_OFFSET_HOURS = get_env_float("TZ_OFFSET_HOURS", 0.0)

files = sorted(glob.glob("data/*.csv"))
if not files:
    raise SystemExit("No CSVs found in data/*.csv")

f = files[0]
df = pd.read_csv(f)
if "time" not in df.columns:
    raise SystemExit(f"{f} missing 'time' column")

df["dt_utc"]   = pd.to_datetime(df["time"], unit="s", utc=True, errors="coerce")
df["dt_local"] = utc_to_local(df["dt_utc"], TZ_OFFSET_HOURS)
hours = df["dt_local"].dt.hour

print("File:", f)
print("\nFirst rows (UTC -> local):\n", df[["time", "dt_utc", "dt_local"]].head().to_string(index=False))
print("\nLocal time range:", df["dt_local"].min(), "->", df["dt_local"].max())
print("\nHour distribution (local):")
print(hours.value_counts().sort_index())
print("\nSESSION raw:", SESSION_RAW, "parsed:", parse_session(SESSION_RAW))
print("TZ_OFFSET_HOURS:", TZ_OFFSET_HOURS)
