import unittest

import main


class TestMarketSymbol(unittest.TestCase):
    def test_to_market_symbol(self):
        cases = {
            "000333": "sz000333",
            "600000": "sh600000",
            "688235": "sh688235",
            "300750": "sz300750",
            "513730": "sh513730",
            "159518": "sz159518",
            "920001": "bj920001",
            "830799": "bj830799",
            "399001": "sz399001",
            "1A0001": "sh000001",
            "1B0015": "sh000015",
            "000922": "sh000922",
        }
        for code, expected in cases.items():
            self.assertEqual(main.to_market_symbol(code), expected, code)


class TestTencentQuotes(unittest.TestCase):
    def test_parse_quotes(self):
        sample = (
            'v_sh600000="1~浦发银行~600000~10.75~10.87~10.80~";\n'
            'v_sz000333="51~美的集团~000333~94.13~94.82~94.28~";\n'
            'v_pv_none_match="1";\n'
        )
        self.assertEqual(
            main._parse_tencent_quotes(sample),
            {"sh600000": 10.75, "sz000333": 94.13},
        )


class TestDividendIndex(unittest.TestCase):
    def test_fetch_dividend_index(self):
        prices = main.get_all_prices(["1B0015"])
        self.assertTrue(prices, "未获取到任何行情数据")
        price = main.find_price(prices, "1B0015")
        self.assertIsNotNone(price, "未找到红利指数(1B0015)行情")
        print(f"[TEST] 红利指数(1B0015) 当前值: {price}")
        self.assertGreater(price, 0)

    def test_fetch_csi_dividend_index(self):
        prices = main.get_all_prices(["000922"])
        self.assertTrue(prices, "未获取到任何行情数据")
        price = main.find_price(prices, "000922")
        self.assertIsNotNone(price, "未找到中证红利(000922)指数行情")
        print(f"[TEST] 中证红利(000922) 当前值: {price}")
        self.assertGreater(price, 0)


if __name__ == "__main__":
    unittest.main()
