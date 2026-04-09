import unittest

from src.signals import compute_signals


class SignalTests(unittest.TestCase):
    def test_expanding_market(self):
        signals = compute_signals(today_total=120, historical_totals=[80, 90, 100])
        self.assertEqual(signals["status"], "expanding")
        self.assertIsNotNone(signals["inventory_growth"])

    def test_stable_on_no_history(self):
        signals = compute_signals(today_total=50, historical_totals=[])
        self.assertEqual(signals["status"], "stable")
        self.assertIsNone(signals["inventory_growth"])


if __name__ == "__main__":
    unittest.main()
