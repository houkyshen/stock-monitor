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


def get_stock_prices():
    try:
        df = ak.stock_zh_a_spot_em()
        df["代码"] = df["代码"].astype(str)
        return df.set_index("代码")
    except Exception:
        pass

    df = ak.stock_zh_a_spot()
    df["代码"] = df["代码"].astype(str)
    return df.set_index("代码")


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

    print(f"[INFO] 开始获取股价数据...")
    try:
        df = get_stock_prices()
    except Exception as e:
        print(f"[ERROR] 获取股价数据失败：{e}")
        sys.exit(1)

    triggered_any = False

    for stock in config["stocks"]:
        if stock.get("triggered", False):
            print(f"[SKIP] {stock['name']}({stock['code']}) 已触发过，跳过")
            continue

        code = stock["code"]
        matched_code = code
        if code not in df.index:
            for prefix in ("sz", "sh", "bj"):
                prefixed = prefix + code
                if prefixed in df.index:
                    matched_code = prefixed
                    break
            else:
                print(f"[WARN] 未找到股票 {stock['name']}({code})，跳过")
                continue

        current_price = float(df.loc[matched_code, "最新价"])
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
