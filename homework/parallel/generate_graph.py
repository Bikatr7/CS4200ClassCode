import matplotlib.pyplot as plt
import numpy as np

elements = np.array([10, 50, 100, 250, 500, 750, 1000, 2500, 5000, 7500, 10000])
times = np.array([0.1246023178100586, 0.002122163772583008, 0.0004119873046875, 0.0005459785461425781, 0.0019719600677490234, 0.008533000946044922, 0.014367818832397461, 0.18611598014831543, 1.0972058773040771, 2.685497999191284, 6.95436692237854])

## hw.model: Mac16,1
## hw.machine: arm64
## hw.ncpu: 10
cpu_name = "Local Mac16,1 (arm64, 10 cores)"

plt.figure(figsize=(10, 6))
plt.plot(elements, times, marker='o', linestyle='-', label=f"{cpu_name} (s)")

plt.xlabel("Number of elements")
plt.ylabel("Time in seconds")
plt.title("Computational Performance: Time vs. Number of Elements")
plt.xticks(elements, rotation=45, ha="right")
plt.legend()
plt.grid(True, which="both", ls="--")
plt.tight_layout()

output_filename = "homework/parallel/runtime_graph.png"
plt.savefig(output_filename)
print(f"Graph saved to {output_filename}")