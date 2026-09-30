# Benchmarking

Benchmark with representative input sizes and record Python, pandas, CPU, memory, and storage type. A basic baseline is:

```bash
python -m timeit -n 3 -r 5 -s "import pandas as pd; from datamedicine import validate; df = pd.read_parquet('large.parquet')" "validate(df)"
```

The analyzers use pandas vectorized reductions. Correlation analysis is quadratic in the number of numeric columns, so consider excluding or sampling very wide datasets in a future configurable analysis profile.
