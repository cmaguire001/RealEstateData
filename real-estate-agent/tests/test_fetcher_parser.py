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
from src.fetcher import _parse_realtor_html


class FetcherParserTests(unittest.TestCase):
    def test_parse_realtor_next_data_payload(self):
        html = '''
        <html>
          <script id="__NEXT_DATA__" type="application/json">
            {
              "props": {
                "pageProps": {
                  "search": {
                    "results": [
                      {
                        "list_price": 425000,
                        "description": {"sqft": 2000, "beds": 4, "baths": 2.5}
                      },
                      {
                        "list_price": 510000,
                        "description": {"sqft": 2500, "beds": 5, "baths": 3}
                      }
                    ]
                  }
                }
              }
            }
          </script>
        </html>
        '''
        rows = _parse_realtor_html(html)
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["price"], 425000)
        self.assertEqual(rows[0]["sqft"], 2000)

    def test_missing_next_data_returns_empty(self):
        rows = _parse_realtor_html("<html><body>no json here</body></html>")
        self.assertEqual(rows, [])


if __name__ == "__main__":
    unittest.main()
