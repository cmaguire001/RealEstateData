import unittest

from src.anoka_fetcher import _normalize_attributes


class AnokaFetcherTests(unittest.TestCase):
    def test_normalize_attributes_with_sale_fields(self):
        attrs = {
            "SALE_PRICE": "375000",
            "LIVING_AREA": "1800",
            "BEDS": "3",
            "BATHS": "2",
        }
        row = _normalize_attributes(attrs)
        self.assertIsNotNone(row)
        self.assertEqual(row["price"], 375000)
        self.assertEqual(row["sqft"], 1800)
        self.assertEqual(row["beds"], 3)
        self.assertEqual(row["baths"], 2.0)

    def test_skips_records_without_price_or_sqft(self):
        self.assertIsNone(_normalize_attributes({"SALE_PRICE": 200000}))
        self.assertIsNone(_normalize_attributes({"LIVING_AREA": 1200}))


if __name__ == "__main__":
    unittest.main()
