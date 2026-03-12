import os
import shutil

ROOT = "/Users/prashanthkumar/Projects/TradingBot/trading-ui/src/components"

MAPPINGS = {
    "trading": ["AssetSelector.jsx", "BrokerAssetSelector.jsx", "MarketRegimePanel.jsx", "MetricsPanel.jsx", "RegimePerformancePanel.jsx", "ReplayControls.jsx", "TradeDetailPanel.jsx", "TradeHistory.jsx", "TradingPanel.jsx"],
    "strategy": ["ActionNode.jsx", "AlgoTradeFlowBackground.jsx", "CodeEditorStrategy.jsx", "ConditionNode.jsx", "DataFlowBackground.jsx", "IndicatorNode.jsx", "OptimizePanel.jsx", "ParameterStrategy.jsx", "RuleBuilder.jsx", "StrategyExplainer.jsx", "StrategyTemplates.jsx"],
    "modals": ["CreateSessionModal.jsx"],
    "ui": ["AppNav.jsx", "CSVUploader.jsx", "ChatInput.jsx", "ErrorBoundary.jsx", "GlassPanel.jsx", "KPICard.jsx", "MarkdownMessage.jsx", "ModelSelector.jsx", "PageTransition.jsx", "ParticleBackground.jsx", "Sidebar.jsx", "ThemeToggle.jsx", "TopToolbar.jsx", "Topbar.jsx"]
}

for folder, files in MAPPINGS.items():
    dst_dir = os.path.join(ROOT, folder)
    os.makedirs(dst_dir, exist_ok=True)
    for f in files:
        src = os.path.join(ROOT, f)
        if os.path.exists(src):
            shutil.move(src, os.path.join(dst_dir, f))
