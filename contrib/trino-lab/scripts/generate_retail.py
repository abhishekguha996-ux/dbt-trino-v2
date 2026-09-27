#!/usr/bin/env python3
"""Create deterministic synthetic fixtures and an independent integer-cents oracle."""

from collections import defaultdict
import csv
from datetime import date, timedelta
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1] / "projects/retail"


def make_data():
    customers = [{"customer_id":i, "customer_name":f"synthetic_{i:03}",
                  "region":["north","south","east","west"][i%4],
                  "referrer_id":i-1 if i%3 == 0 else None} for i in range(1,51)]
    products = [{"product_id":i,"product_name":f"item_{i:03}",
                 "category":["coffee","food","gear"][i%3],
                 "unit_cents":500+37*i} for i in range(1,21)]
    orders, lines, payments, refunds = [], [], [], []
    totals = {}
    for oid in range(1,201):
        status = "cancelled" if oid%17 == 0 else "complete"
        orders.append({"order_id":oid,"customer_id":(oid*7)%45+1,
                       "order_date":str(date(2026,1,1)+timedelta(days=oid%28)),"status":status})
        gross = 0
        for j in range(2+oid%2):
            pid=(oid*3+j)%20+1
            qty=(oid+j)%3+1
            unit=products[pid-1]["unit_cents"]
            lines.append({"line_id":len(lines)+1,"order_id":oid,"product_id":pid,
                          "quantity":qty,"unit_cents":unit})
            gross += qty*unit
        paid = gross if status == "complete" and oid%13 else 0
        if paid:
            pieces = [paid//2,paid-paid//2] if oid%5 == 0 else [paid]
            for amount in pieces:
                payments.append({"payment_id":len(payments)+1,"order_id":oid,"amount_cents":amount})
        refunded = paid//7 if paid and oid%11 == 0 else 0
        if refunded:
            pieces = [refunded//2,refunded-refunded//2] if oid%22 == 0 else [refunded]
            for amount in pieces:
                refunds.append({"refund_id":len(refunds)+1,"order_id":oid,"amount_cents":amount})
        totals[oid] = {"gross_cents":gross,"paid_cents":paid,"refund_cents":refunded,"net_cents":paid-refunded}
    # Oracle uses known order events, independent of the SQL join implementation.
    expected_customers = {c["customer_id"]:{"customer_id":c["customer_id"],"order_count":0,"gross_cents":0,"net_cents":0}
                          for c in customers}
    daily=defaultdict(lambda:{"order_count":0,"gross_cents":0,"net_cents":0})
    expected_orders=[]
    for order in orders:
        values=totals[order["order_id"]]
        expected_orders.append({"order_id":order["order_id"],**values})
        for aggregate in (expected_customers[order["customer_id"]],daily[order["order_date"]]):
            aggregate["order_count"] += 1
            aggregate["gross_cents"] += values["gross_cents"]
            aggregate["net_cents"] += values["net_cents"]
    return {"raw_customers":customers,"raw_products":products,"raw_orders":orders,
            "raw_order_lines":lines,"raw_payments":payments,"raw_refunds":refunds,
            "expected_orders":expected_orders,"expected_customers":list(expected_customers.values()),
            "expected_daily":[{"order_date":day,**daily[day]} for day in sorted(daily)]}


def main():
    data=make_data()
    (ROOT/"seeds").mkdir(parents=True,exist_ok=True)
    for name, rows in data.items():
        with (ROOT/"seeds"/f"{name}.csv").open("w",newline="") as output:
            writer=csv.DictWriter(output,fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
    summary={"rows":{name:len(rows) for name,rows in data.items()},
             "totals":{key:sum(row[key] for row in data["expected_orders"])
                       for key in ("gross_cents","paid_cents","refund_cents","net_cents")},
             "customers_without_orders":sum(row["order_count"] == 0 for row in data["expected_customers"])}
    (ROOT/"expected.json").write_text(json.dumps(summary,indent=2)+"\n")
    print(json.dumps(summary,indent=2))


if __name__ == "__main__":
    main()
