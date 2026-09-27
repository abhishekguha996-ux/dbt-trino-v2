from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from generate_retail import make_data


class RetailTests(unittest.TestCase):
    def test_fixture_contract(self):
        data=make_data()
        self.assertEqual(len(data["raw_customers"]),50)
        self.assertEqual(len(data["raw_orders"]),200)
        self.assertEqual(len(data["raw_order_lines"]),500)
        self.assertEqual(sum(r["order_count"] == 0 for r in data["expected_customers"]),5)
        self.assertEqual(sum(r["net_cents"] for r in data["expected_orders"]),757230)
        self.assertEqual(sum(r["gross_cents"] for r in data["expected_orders"]),891460)

    def test_raw_payment_events_match_oracle(self):
        data=make_data()
        paid=sum(r["amount_cents"] for r in data["raw_payments"])
        refunded=sum(r["amount_cents"] for r in data["raw_refunds"])
        self.assertEqual(paid,767351)
        self.assertEqual(refunded,10121)
        self.assertEqual(paid-refunded,sum(r["net_cents"] for r in data["expected_daily"]))
        for line in data["raw_order_lines"]:
            self.assertTrue(1 <= line["order_id"] <= 200)
            self.assertTrue(1 <= line["product_id"] <= 20)


if __name__ == "__main__":
    unittest.main()
