import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path
from scipy import stats
import statsmodels.api as sm

result_dir = Path('results')
output_dir = Path('results/analysis')
output_dir.mkdir(exist_ok=True)

df = pd.read_csv(result_dir / "Encrypt_results.csv")
print('Data loaded')
print(f'Total rows: {len(df)}\n')

print('\n')
print("1. Throughput Analysis (MB/s)")
print('\n')

df_perf = df[df["Category"].isin(["Hashing","Symmetric"])].copy()
df_perf["Throughput_MBps"] = (df_perf["FileSize_KB"] / 1024) / df_perf["Time_sec"]
throughput_summary = (
    df_perf.groupby(["Category","Algorithm"])["Throughput_MBps"]
    .agg(["mean","std","min","max"])
    .round(2)
)
print("\nThroughput Summary:")
print(throughput_summary)
throughput_summary.to_csv(output_dir/"throughput_summary.csv")

print('\n')
print('2. Relative Performance')
print('\n')

def relative_speed(category):
    subset = df_perf[df_perf["Category"] == category]
    pivot = subset.pivot_table(
        index = "FileSize_KB",
        columns = "Algorithm",
        values = "Time_sec"
    )
    baseline = pivot.min(axis = 1)
    relative = pivot.div(baseline, axis = 0).round(2)
    print(f"\n{category} - Relative Time (1.0 = fastest):")
    print(relative)
    return relative
hash_rel = relative_speed("Hashing")
sym_rel = relative_speed("Symmetric")

hash_rel.to_csv(output_dir / "Hashing_relative.csv")
sym_rel.to_csv(output_dir/ 'Symmetric_relative.csv')

print("3. Descriptive Statistics")
desc = (
    df.groupby(["Category",'Algorithm'])['Time_sec']
    .agg(['count','mean','std','min','max'])
    .round(6)
)
print(desc)
desc.to_csv(output_dir / "Descriptive_stats.csv")

print('\n')
print('4. Linear Regression')
print('\n')

regression = []
for category in ["Hashing", "Symmetric"]:
    category_df = df[df["Category"] == category]
    for algorithm in category_df["Algorithm"].unique():
        algorithm_df = category_df[category_df["Algorithm"] == algorithm]

        x = sm.add_constant(algorithm_df["FileSize_KB"])
        model = sm.OLS(algorithm_df["Time_sec"], x).fit()

        slope= model.params.iloc[1]
        r2 = model.rsquared
        pval = model.pvalues.iloc[1]

        print(f"{category} - {algorithm}:")
        print(f"  Slope     : {slope:.8f}")
        print(f"  R-squared : {r2:.4f}")
        print(f"  P-value   : {pval:.6f}\n")
        
        regression.append({
            "Category": category,
            "Algorithm": algorithm,
            "Slope": round(slope, 8),
            "R_squared": round(r2, 4),
            "P_value": round(pval, 6)
        })
pd.DataFrame(regression).to_csv(output_dir/"regression.csv", index=False)

print('\n')
print('5.ANOVA')
print('\n')
anova_result = []
def run_anova(category):
    groups = [g["Time_sec"].values for _, g in df[df["Category"] == category].groupby("Algorithm")]
    f_stat, p_value = stats.f_oneway(*groups)

    print(f"\nANOVA - {category}")
    print(f"F-statistic : {f_stat:.4f}")
    print(f"P-value     : {p_value:.6f}")

    if p_value < 0.05:
        significance = "Statistically significant difference"
        print(significance)
    else:
        significance = "No statistically significant difference"
        print(significance)
    anova_result.append({
        "Category": category,
        "F_statistic": round(f_stat, 4),
        "P_value": round(p_value, 6),
        "Result": significance
    })
run_anova("Hashing")
run_anova("Symmetric")

pd.DataFrame(anova_result).to_csv(output_dir / 'anova_result.csv', index=False)
print("\nANOVA results saved to: anova_result.csv")

print('\n')
print('6.Graphs')
print('\n')

plt.figure(figsize=(10, 6))
df_perf.groupby(["Category", "Algorithm"])["Throughput_MBps"].mean().unstack().plot(kind="bar", ax=plt.gca())
plt.title("Average Throughput Comparison (MB/s)")
plt.ylabel("Throughput (MB/s)")
plt.xticks(rotation=0)
plt.tight_layout()
plt.savefig(output_dir / "throughput_bar.png", dpi=300)
plt.close()
print("Saved: throughput_bar.png")

plt.figure(figsize=(10, 6))
for algo in df[df["Category"] == "Hashing"]["Algorithm"].unique():
    subset = df[(df["Category"] == "Hashing") & (df["Algorithm"] == algo)]
    plt.plot(subset["FileSize_KB"], subset["Time_sec"], marker='o', label=algo)
plt.title("Hashing Algorithms - Time vs File Size")
plt.xlabel("File Size (KB)")
plt.ylabel("Time (seconds)")
plt.legend()
plt.grid(True)
plt.savefig(output_dir / "hashing_time.png", dpi=300)
plt.close()
print("Saved: hashing_time.png")

plt.figure(figsize=(10, 6))
for algo in df[df["Category"] == "Symmetric"]["Algorithm"].unique():
    subset = df[(df["Category"] == "Symmetric") & (df["Algorithm"] == algo)]
    plt.plot(subset["FileSize_KB"], subset["Time_sec"], marker='o', label=algo)
plt.title("Symmetric Algorithms - Time vs File Size")
plt.xlabel("File Size (KB)")
plt.ylabel("Time (seconds)")
plt.legend()
plt.grid(True)
plt.savefig(output_dir / "symmetric_time.png", dpi=300)
plt.close()
print("Saved: symmetric_time.png")

print("Generating Relative Performance chart")

fig, axes = plt.subplots(1, 2, figsize=(14, 6))

hash_rel.mean().plot(kind="bar", ax=axes[0], color=["#2ca02c", "#1f77b4", "#ff7f0e"])
axes[0].set_title("Hashing - Average Relative Time\n(1.0 = Fastest)")
axes[0].set_ylabel("Relative Time")
axes[0].set_xlabel("Algorithm")
axes[0].tick_params(axis='x', rotation=0)
axes[0].axhline(y=1.0, color='gray', linestyle='--', linewidth=1)


sym_rel.mean().plot(kind="bar", ax=axes[1], color=["#1f77b4", "#2ca02c", "#d62728"])
axes[1].set_title("Symmetric - Average Relative Time\n(1.0 = Fastest)")
axes[1].set_ylabel("Relative Time")
axes[1].set_xlabel("Algorithm")
axes[1].tick_params(axis='x', rotation=0)
axes[1].axhline(y=1.0, color='gray', linestyle='--', linewidth=1)

plt.tight_layout()
plt.savefig(output_dir / "relative_performance.png", dpi=300)
plt.close()
print("Saved: relative_performance.png")

print("Generating Asymmetric Key Generation chart")

asym_keygen = df[df["Category"] == "Asymmetric-KeyGen"]

plt.figure(figsize=(8, 5))
plt.bar(asym_keygen["Algorithm"], asym_keygen["Time_sec"], color=["#1f77b4", "#ff7f0e", "#2ca02c"])
plt.title("Asymmetric Algorithms - Key Generation Time")
plt.ylabel("Time (seconds)")
plt.xlabel("Algorithm")
plt.grid(axis='y', linestyle='--', alpha=0.7)
plt.tight_layout()
plt.savefig(output_dir / "asymmetric_keygen.png", dpi=300)
plt.close()
print("Saved: asymmetric_keygen.png")

print("Generating Asymmetric Operation chart")

asym_op = df[df["Category"] == "Asymmetric-Operation"]

plt.figure(figsize=(8, 5))
plt.bar(asym_op["Algorithm"], asym_op["Time_sec"], color=["#1f77b3", "#ff7f04", "#2ca022"])
plt.title("Asymmetric Algorithms - Operation Time")
plt.ylabel("Time (seconds)")
plt.xlabel("Algorithm")
plt.grid(axis='y', linestyle='--', alpha=0.7)
plt.tight_layout()
plt.savefig(output_dir / "asymmetric_operation.png", dpi=300)
plt.close()
print("Saved: asymmetric_op.png")

print("\n")
print("Analysis completed successfully!")
print(f"All files saved to: {output_dir}")
print("\n")