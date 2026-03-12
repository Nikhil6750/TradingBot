import optuna
import pandas as pd
from typing import Dict, Any
from backend.strategy_engine import run_strategy

def run_optimization(df: pd.DataFrame, base_config: Dict[str, Any], param_ranges: Dict[str, list], n_trials: int = 50) -> Dict[str, Any]:
    """
    Intelligently searches optimal parameters using Bayesian Optimization (Optuna).
    
    Args:
        df: The pandas DataFrame holding the market candles.
        base_config: The foundational config object dictating mode/strategy.
        param_ranges: A dictionary of parameters mapping to a range [min, max] or list of choices. 
                 E.g. {"short_ma": [5, 50], "long_ma": [20, 200]}
        n_trials: Maximum number of trials to run.
                 
    Returns:
        Dict: best_parameters, best_score, optimization_history
    """
    
    optimization_history = []
    
    def objective(trial):
        # Create a deep copy of the active testing config 
        test_config = dict(base_config)
        test_params = dict(test_config.get("parameters", {}))
        
        # Build the dynamic grid combination for this trial
        combo_dict = {}
        for param, r in param_ranges.items():
            if isinstance(r, list) and len(r) == 2 and all(isinstance(x, int) for x in r):
                # Suggest integer range
                combo_dict[param] = trial.suggest_int(param, r[0], r[1])
            elif isinstance(r, list) and len(r) == 2 and any(isinstance(x, float) for x in r):
                # Suggest float range
                combo_dict[param] = trial.suggest_float(param, float(r[0]), float(r[1]))
            elif isinstance(r, list):
                # Categorical choice if arbitrary list
                combo_dict[param] = trial.suggest_categorical(param, r)
            else:
                # Fallback
                combo_dict[param] = trial.suggest_categorical(param, [r])
                
        test_params.update(combo_dict)
        test_config["parameters"] = test_params
        
        try:
            # Execute the engine
            run_output = run_strategy(df, test_config)
            metrics = run_output.get("metrics", {})
            
            # Extract Key Metrics
            ret = metrics.get("total_return", 0)
            win_rate = metrics.get("win_rate", 0)
            drawdown = metrics.get("max_drawdown", 0)
            sharpe = metrics.get("sharpe_ratio", 0)
            
            # Save attributes so we can extract them later for history
            trial.set_user_attr("total_return", ret)
            trial.set_user_attr("win_rate", win_rate)
            trial.set_user_attr("max_drawdown", drawdown)
            trial.set_user_attr("sharpe_ratio", sharpe)
            
            # We are maximizing Sharpe Ratio as the primary objective indicator
            return sharpe
            
        except Exception as e:
            # Optuna can handle failed trials by pruning them or returning a very bad score
            raise optuna.TrialPruned(f"Execution failed: {e}")
            
    # Suppress optuna logging stdout for clean server output
    optuna.logging.set_verbosity(optuna.logging.WARNING)
    
    # Create Study aiming to maximize
    study = optuna.create_study(direction="maximize")
    study.optimize(objective, n_trials=n_trials)
    
    if len(study.trials) == 0 or study.best_trial is None:
        raise ValueError("Optimization yielded zero valid combinations. Check parameter bounds.")
        
    # Extract History
    for t in study.trials:
        if t.state == optuna.trial.TrialState.COMPLETE:
            entry = {**t.params}
            entry["Return"] = t.user_attrs.get("total_return", 0)
            entry["Win Rate"] = t.user_attrs.get("win_rate", 0)
            entry["Max Drawdown"] = t.user_attrs.get("max_drawdown", 0)
            entry["Sharpe Ratio"] = t.value # The objective value
            optimization_history.append(entry)
            
    # Formulate top results dataframe
    res_df = pd.DataFrame(optimization_history)
    if not res_df.empty:
        res_df = res_df.sort_values(by=["Sharpe Ratio", "Return"], ascending=[False, False])
        top_results = res_df.to_dict(orient="records")[:10]
    else:
        top_results = []
    
    best_params = study.best_params
    
    return {
        "best_parameters": best_params,
        "best_score": study.best_value,
        "optimization_history": top_results
    }
