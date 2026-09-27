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

Each project's `profiles.yml` targets the local stack (`python3 scripts/stack.py up`):
`iceberg` over plain HTTP with `method: none`, and `hive` over HTTPS with password
authentication and the stack's generated CA. The credentials are synthetic lab values.

Both projects run in the functional suite (`functional/test_projects.py`) on the Memory,
Hive, Iceberg and Delta Lake catalogs and are compared with the independent Python results.
