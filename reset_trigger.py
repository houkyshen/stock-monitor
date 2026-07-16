"""重置所有已触发的股票状态，使其重新开始监控。"""
import os
import json

CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "stocks.json")


def main():
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        config = json.load(f)

    reset_count = 0
    for stock in config["stocks"]:
        if stock.get("triggered"):
            stock["triggered"] = False
            reset_count += 1
            print(f"[RESET] {stock['name']}({stock['code']})")

    if reset_count == 0:
        print("没有需要重置的股票")
        return

    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)

    print(f"\n已重置 {reset_count} 只股票状态，下次运行将重新监控。")


if __name__ == "__main__":
    main()
