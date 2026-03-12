import os
import re

SRC_DIR = "/Users/prashanthkumar/Projects/TradingBot/trading-ui/src"
MOVED = {
    "AssetSelector": "trading", "BrokerAssetSelector": "trading", "MarketRegimePanel": "trading",
    "MetricsPanel": "trading", "RegimePerformancePanel": "trading", "ReplayControls": "trading",
    "TradeDetailPanel": "trading", "TradeHistory": "trading", "TradingPanel": "trading",
    "ActionNode": "strategy", "AlgoTradeFlowBackground": "strategy", "CodeEditorStrategy": "strategy",
    "ConditionNode": "strategy", "DataFlowBackground": "strategy", "IndicatorNode": "strategy",
    "OptimizePanel": "strategy", "ParameterStrategy": "strategy", "RuleBuilder": "strategy",
    "StrategyExplainer": "strategy", "StrategyTemplates": "strategy", "CreateSessionModal": "modals",
    "AppNav": "ui", "CSVUploader": "ui", "ChatInput": "ui", "ErrorBoundary": "ui",
    "GlassPanel": "ui", "KPICard": "ui", "MarkdownMessage": "ui", "ModelSelector": "ui",
    "PageTransition": "ui", "ParticleBackground": "ui", "Sidebar": "ui", "ThemeToggle": "ui",
    "TopToolbar": "ui", "Topbar": "ui"
}

for root, dirs, files in os.walk(SRC_DIR):
    for f in files:
        if not f.endswith(('.jsx', '.js')): continue
        filepath = os.path.join(root, f)
        with open(filepath, 'r') as file: content = file.read()
        new = content
        for comp, dst_folder in MOVED.items():
            new = re.sub(r'(from\s+[\'"]\.\./components/)' + comp + r'([\'"])', r'\g<1>' + dst_folder + '/' + comp + r'\g<2>', new)
            new = re.sub(r'(from\s+[\'"]\./components/)' + comp + r'([\'"])', r'\g<1>' + dst_folder + '/' + comp + r'\g<2>', new)
            if "components" in root:
                cur_folder = os.path.basename(root)
                if cur_folder in MOVED.values():
                    pattern = r'(from\s+[\'"]\./)' + comp + r'([\'"])'
                    if dst_folder == cur_folder: pass
                    else: new = re.sub(pattern, f'from "../{dst_folder}/{comp}\\2"', new)
        if new != content:
            with open(filepath, 'w') as file: file.write(new)
