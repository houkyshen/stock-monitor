import os
import json
import smtplib
import sys
from email.mime.text import MIMEText
from email.header import Header
from datetime import datetime

import akshare as ak

CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "stocks.json")


def load_config():
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_config(config):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)


def get_all_prices():
    prices = {}

    sources = [
        ("东方财富股票", lambda: ak.stock_zh_a_spot_em()),
        ("新浪股票", lambda: ak.stock_zh_a_spot()),
        ("东方财富ETF", lambda: ak.fund_etf_spot_em()),
    ]

    for name, fetcher in sources:
        try:
            df = fetcher()
            for _, row in df.iterrows():
                code = str(row["代码"])
                if code not in prices:
                    prices[code] = float(row["最新价"])
            print(f"[INFO] {name}数据获取成功，共 {len(df)} 条")
        except Exception as e:
            print(f"[WARN] {name}数据获取失败: {e}")

    return prices


def find_price(prices, code):
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

    print("[INFO] 开始获取股价数据...")
    prices = get_all_prices()
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
