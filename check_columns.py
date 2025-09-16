import pandas as pd

# Replace the filename below with your actual data file
df = pd.read_csv("data/FX_EURJPY, 5_abeeb.csv")

print("Columns in file:")
print(df.columns.tolist())
