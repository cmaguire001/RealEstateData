import unittest

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
