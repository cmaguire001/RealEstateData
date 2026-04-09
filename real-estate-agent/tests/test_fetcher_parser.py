import unittest

from src.fetcher import _iter_rows, _normalize_listing


class FetcherNormalizationTests(unittest.TestCase):
    def test_normalize_pyrealtor_style_row(self):
        row = {
            "Price": "$425,000",
            "Square Footage": "2000",
            "Bedrooms": "4",
            "Bathrooms": "2.5",
        }
        normalized = _normalize_listing(row)
        self.assertIsNotNone(normalized)
        self.assertEqual(normalized["price"], 425000)
        self.assertEqual(normalized["sqft"], 2000)
        self.assertEqual(normalized["beds"], 4)
        self.assertEqual(normalized["baths"], 2.5)

    def test_iter_rows_list_dict_passthrough(self):
        rows = _iter_rows([{"Price": 1}, {"Price": 2}, "bad"])
        self.assertEqual(len(rows), 2)


if __name__ == "__main__":
    unittest.main()
