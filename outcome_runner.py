from bot.outcome_tracker import evaluate_outcomes

if __name__ == "__main__":
    # Point to the file main.py is creating
    evaluate_outcomes(results_file="data/results.csv", data_dir="data")
