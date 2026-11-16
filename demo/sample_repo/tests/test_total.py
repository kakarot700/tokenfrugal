import unittest

from inventory.total import line_value, total_value


class TotalTest(unittest.TestCase):
    def test_line_value_uses_quantity(self):
        self.assertEqual(line_value({"price": 10, "qty": 3}), 30)

    def test_total_value(self):
        items = [{"price": 10, "qty": 3}, {"price": 5, "qty": 2}]
        self.assertEqual(total_value(items), 40)


if __name__ == "__main__":
    unittest.main()
