import os
import json
import smtplib
import sys
from email.mime.text import MIMEText
from email.header import Header
from datetime import datetime

import akshare as ak
import requests

CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "stocks.json")

INDEX_CODE_MAP = {
    "1A0001": "sh000001",
    "1B0688": "sh000688",
    "1B0015": "sh000015",
    "000922": "sh000922",
}

# 腾讯批量行情接口，一次请求可取回所有股票/ETF/指数的最新价
TENCENT_QUOTE_URL = "https://qt.gtimg.cn/q="
TENCENT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Referer": "https://gu.qq.com/",
}
TENCENT_BATCH_SIZE = 60


def _ak(name, *aliases):
    """按名称获取 akshare 接口，兼容 akshare 升级后的接口重命名。"""
    for candidate in (name, *aliases):
        func = getattr(ak, candidate, None)
        if callable(func):
            return func
    raise AttributeError(f"当前 akshare 版本不提供接口: {name}（别名: {', '.join(aliases)}）")


def load_config():
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_config(config):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)


def to_market_symbol(code):
    """把股票/ETF/指数代码转换成腾讯行情代码，例如 000333 -> sz000333。"""
    code = str(code).strip()
    if code in INDEX_CODE_MAP:
        return INDEX_CODE_MAP[code]
    if code[:2].lower() in ("sh", "sz", "bj"):
        return code.lower()
    if not code.isdigit():
        return None
    if code.startswith("92"):  # 北交所新代码
        return "bj" + code
    if code.startswith(("5", "6", "9")):  # 沪市股票、ETF、B 股
        return "sh" + code
    if code.startswith(("4", "8")):  # 北交所
        return "bj" + code
    return "sz" + code


def _parse_tencent_quotes(text):
    """解析腾讯行情返回内容，形如：v_sh600000="1~浦发银行~600000~10.75~...";"""
    prices = {}
    for chunk in text.split(";"):
        chunk = chunk.strip()
        if not chunk.startswith("v_"):
            continue
        symbol, _, payload = chunk.partition("=")
        fields = payload.strip().strip('"').split("~")
        if len(fields) < 4:
            continue
        try:
            price = float(fields[3])
        except ValueError:
            continue
        if price > 0:
            prices[symbol[2:]] = price
    return prices


def fetch_tencent_prices(codes):
    """通过腾讯行情接口批量获取最新价，返回 {市场代码: 价格}。"""
    symbols = []
    for code in codes:
        symbol = to_market_symbol(code)
        if symbol and symbol not in symbols:
            symbols.append(symbol)

    prices = {}
    for start in range(0, len(symbols), TENCENT_BATCH_SIZE):
        batch = symbols[start:start + TENCENT_BATCH_SIZE]
        resp = requests.get(
            TENCENT_QUOTE_URL + ",".join(batch),
            headers=TENCENT_HEADERS,
            timeout=20,
        )
        resp.raise_for_status()
        resp.encoding = "gbk"
        prices.update(_parse_tencent_quotes(resp.text))
    return prices


def get_all_prices(codes=None):
    """获取行情价格，返回 {代码或带市场前缀的代码: 最新价}。"""
    if codes is None:
        try:
            codes = [stock["code"] for stock in load_config()["stocks"]]
        except Exception as e:
            print(f"[WARN] 读取监控列表失败，改为拉取全市场行情: {e}")
            codes = None

    prices = {}

    # 优先用腾讯批量行情：一次请求即可覆盖股票、ETF、指数，且不易被限流
    if codes:
        try:
            prices.update(fetch_tencent_prices(codes))
            matched = sum(1 for code in codes if find_price(prices, code) is not None)
            print(f"[INFO] 腾讯行情获取成功，匹配 {matched}/{len(codes)} 个代码")
        except Exception as e:
            print(f"[WARN] 腾讯行情获取失败: {e}")

        missing = [code for code in codes if find_price(prices, code) is None]
        if not missing:
            return prices
        print(f"[WARN] 腾讯行情未覆盖以下代码，尝试备用数据源: {', '.join(missing)}")
    else:
        missing = None

    sources = [
        ("东方财富股票", lambda: _ak("stock_zh_a_spot_em")()),
        ("新浪股票", lambda: _ak("stock_zh_a_spot", "stock_zh_a_spot_sina")()),
        ("东方财富ETF", lambda: _ak("fund_etf_spot_em")()),
        ("新浪ETF", lambda: _ak("fund_etf_category_sina")(symbol="ETF基金")),
        ("新浪指数", lambda: _ak("stock_zh_index_spot_sina", "index_zh_spot_sina")()),
    ]

    for name, fetcher in sources:
        try:
            df = fetcher()
            for _, row in df.iterrows():
                code = str(row["代码"])
                if code not in prices:
                    try:
                        prices[code] = float(row["最新价"])
                    except (TypeError, ValueError):
                        continue
            print(f"[INFO] {name}数据获取成功，共 {len(df)} 条")
        except Exception as e:
            print(f"[WARN] {name}数据获取失败: {e}")

    index_fetchers = (
        lambda symbol: _ak("stock_zh_index_daily_tx", "index_zh_daily_tx")(symbol=symbol),
        lambda symbol: _ak("stock_zh_index_daily", "index_zh_daily_sina")(symbol=symbol),
    )
    for stock_code, index_code in INDEX_CODE_MAP.items():
        if index_code in prices:
            continue
        if missing is not None and stock_code not in missing:
            continue
        for fetcher in index_fetchers:
            try:
                df = fetcher(index_code)
                price = float(df.iloc[-1]["close"])
                prices[index_code] = price
                print(f"[INFO] 指数{index_code}数据获取成功，最新收盘 {price}")
                break
            except Exception as e:
                print(f"[WARN] 指数{index_code}日线接口获取失败: {e}")

    return prices


def find_price(prices, code):
    # 指数类代码只认映射后的指数行情，避免误匹配到同名的其他标的
    if code in INDEX_CODE_MAP:
        return prices.get(INDEX_CODE_MAP[code])
    if code in prices:
        return prices[code]
    for prefix in ("sz", "sh", "bj"):
        prefixed = prefix + code
        if prefixed in prices:
            return prices[prefixed]
    return None


def send_email(config, stock):
    email_cfg = config["email"]
    password = os.getenv("EMAIL_PASSWORD", "")
    if not password:
        print("[WARN] EMAIL_PASSWORD 环境变量未设置，跳过发送邮件")
        return

    direction_text = "下跌至" if stock["direction"] == "le" else "上涨至"
    subject = f"[股价提醒] {stock['name']}({stock['code']}) 已{direction_text} {stock['trigger_price']}"

    body = f"""股票名称：{stock['name']}
股票代码：{stock['code']}
当前价格：{stock['current_price']}
触发价格：{stock['trigger_price']}
触发方向：{'<= （下跌至）' if stock['direction'] == 'le' else '>= （上涨至）'}
备注：{stock.get('comment', '')}
提醒时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""

    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = Header(subject, "utf-8")
    msg["From"] = email_cfg["sender"]
    msg["To"] = email_cfg["receiver"]

    try:
        server = smtplib.SMTP_SSL(email_cfg["smtp_server"], email_cfg["smtp_port"])
        server.login(email_cfg["sender"], password)
        server.sendmail(email_cfg["sender"], [email_cfg["receiver"]], msg.as_string())
        server.quit()
        print(f"[OK] 邮件已发送：{subject}")
    except Exception as e:
        print(f"[ERROR] 邮件发送失败：{e}")


def main():
    config = load_config()
    codes = [stock["code"] for stock in config["stocks"]]

    print("[INFO] 开始获取股价数据...")
    prices = get_all_prices(codes)
    if not prices:
        print("[ERROR] 无法获取任何股价数据")
        sys.exit(1)

    triggered_any = False

    for stock in config["stocks"]:
        if stock.get("triggered", False):
            print(f"[SKIP] {stock['name']}({stock['code']}) 已触发过，跳过")
            continue

        code = stock["code"]
        current_price = find_price(prices, code)
        if current_price is None:
            print(f"[WARN] 未找到股票 {stock['name']}({code})，跳过")
            continue

        trigger_price = stock["trigger_price"]
        direction = stock.get("direction", "le")

        if direction == "le":
            condition_met = current_price <= trigger_price
        else:
            condition_met = current_price >= trigger_price

        op = "<=" if direction == "le" else ">="

        if condition_met:
            print(f"[TRIGGERED] {stock['name']}({code}) 当前价 {current_price} {op} 触发价 {trigger_price}")
            stock["current_price"] = current_price
            send_email(config, stock)
            stock["triggered"] = True
            triggered_any = True
        else:
            print(f"[OK] {stock['name']}({code}) 当前价 {current_price}，未触发（需 {op} {trigger_price}）")

    if triggered_any:
        save_config(config)
        print("[INFO] stocks.json 已更新")
    else:
        print("[INFO] 本次无新触发")


if __name__ == "__main__":
    main()
