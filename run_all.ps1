# ---- prevent overlapping runs ----
$lock = "D:\Trading Bot\.run.lock"
if (Test-Path $lock) { Write-Host "[run_all] Another run in progress. Exiting."; exit 0 }
New-Item -ItemType File -Path $lock -Force | Out-Null
try {
    # (your existing env + pipeline code stays below)

# ====== favorite settings (adjust only if needed) ======
$env:DATA_DIR            = "D:\Trading Bot\data"
$env:SYMBOL_ALLOWLIST    = "GBPAUD,EURJPY,EURUSD"  # GBPAUD first (it’s leading)
$env:HOUR_ALLOW          = "15-18"                 # start narrow, expand later if justified
$env:THRESHOLD           = "50"
$env:ATR_MULTIPLIER      = "2.0"
$env:RR                  = "2.0"
$env:COOLDOWN_BARS       = "8"
$env:MIN_ATR_PCT         = "0.0002"
$env:AUTO_SYNTHETIC_WHEN_EMPTY = "1"              # set 0 to force real-score only
$env:PATTERN_COLS        = "Pattern Alert,Pattern_Alert,pattern_alert,score,confidence,prob"
$env:SESSION             = "ALL"
$env:TRUNCATE_RESULTS    = "1"
$env:DRY_RUN             = "1"                    # keep 1 for paper; flip to 0 when ready

# ====== run the pipeline ======
python backtest_runner.py
python performance_report.py
python equity_curve.py
python audit_insights.py

}
finally {
    Remove-Item $lock -ErrorAction SilentlyContinue
}
