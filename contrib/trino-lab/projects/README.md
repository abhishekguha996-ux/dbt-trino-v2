These projects use synthetic data only.

`retail` has 50 customers, 20 products, 200 orders, 500 order lines, split
payments, refunds, and five customers without orders. Run
`python3 scripts/generate_retail.py` at the lab root to reproduce its CSV files.
Expected order, customer, and daily results come from a separate Python
calculation. Money uses integer cents.

`tpch` reads Trino's generated `tpch.tiny` catalog and writes two revenue models
into the lab's writable catalog. Its joins are inspired by TPC-H Q3 and Q5. This
is a correctness fixture, not a TPC benchmark or a performance claim. Trino's
catalog configuration must use standard column names, without the `c_`, `o_`, or
`l_` prefixes.

Profiles are for the private disposable lab: synthetic user, no password, no
published ports. Plain HTTP is explicit for this isolated test environment.
Use TLS with certificate verification for authenticated external connections.

The models and tests must run through the modified source-built dbt executable
before adapter support can be claimed. A direct driver test is a separate gate.
