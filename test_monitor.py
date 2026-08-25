import unittest

import main


class TestDividendIndex(unittest.TestCase):
    def test_fetch_dividend_index(self):
        prices = main.get_all_prices()
        self.assertTrue(prices, "未获取到任何行情数据")
        price = main.find_price(prices, "1B0015")
        self.assertIsNotNone(price, "未找到红利指数(1B0015)行情")
        print(f"[TEST] 红利指数(1B0015) 当前值: {price}")
        self.assertGreater(price, 0)

    def test_fetch_csi_dividend_index(self):
        prices = main.get_all_prices()
        self.assertTrue(prices, "未获取到任何行情数据")
        price = main.find_price(prices, "000922")
        self.assertIsNotNone(price, "未找到中证红利(000922)指数行情")
        print(f"[TEST] 中证红利(000922) 当前值: {price}")
        self.assertGreater(price, 0)


if __name__ == "__main__":
    unittest.main()
