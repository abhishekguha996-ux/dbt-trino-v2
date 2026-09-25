These projects use synthetic data only.

`retail` has 50 customers, 20 products, 200 orders, 500 order lines, split
payments, refunds, and five customers without orders. Run
`python3 scripts/generate_retail.py` at the lab root to regenerate its sales CSV files. `edge_values.csv` is a separate fixed edge-case fixture.
Expected order, customer, and daily results come from a separate Python
calculation. Money uses integer cents.

`tpch` reads Trino's generated `tpch.tiny` catalog and writes two revenue models
into the lab's writable catalog. Its joins are inspired by TPC-H Q3 and Q5. This
is a correctness fixture, not a TPC benchmark or a performance claim. Trino's
catalog configuration uses `tpch.column-naming=STANDARD`, with the `c_`, `o_`,
and `l_` prefixes. Output model columns use shorter aliases.

Profiles are for the private disposable lab: synthetic user, no password, no
published ports. Plain HTTP is explicit for this isolated test environment.
Use TLS with certificate verification for authenticated external connections.

These models passed through the modified source-built dbt executable. See
[the validation record](../TEST-RESULTS.md) for results and limits. Direct driver
tests are reported separately.
