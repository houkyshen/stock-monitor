# 股票价格提醒工具

通过 GitHub Actions 定时监控 A 股股价，当股价触及设定条件时发送 QQ 邮件通知。

## 项目结构

```
stock-monitor/
├── pyproject.toml                  # uv 项目配置，依赖 akshare
├── stocks.json                     # 股票监控列表 + 触发状态（运行时更新）
├── main.py                         # 核心监控脚本
├── test_monitor.py                 # 单元测试（代码映射/行情解析）+ 行情联通性测试
├── reset_trigger.py               # 重置所有已触发股票状态
├── .github/workflows/monitor.yml  # GitHub Actions 定时任务（每晚 19:00 北京时间）
└── .gitignore
```

## 数据来源

行情按以下顺序获取，前一级失败会自动降级到下一级：

1. **腾讯批量行情**（`qt.gtimg.cn`）：一次请求即可取回所有股票、ETF、指数的最新价，速度快、不易被限流，是默认数据源；
2. **akshare 全市场行情**：东方财富股票/ETF、新浪股票/ETF、新浪指数；
3. **akshare 指数日线**：腾讯日线、新浪日线。

> akshare 从 1.20.x 起重命名了部分接口（如 `stock_zh_a_spot` → `stock_zh_a_spot_sina`）。
> `main.py` 中的 `_ak()` 会同时兼容新旧接口名，升级 akshare 后不会因为改名而失效。

## 快速开始

### 1. 本地运行

```bash
uv sync
uv run python main.py
```

### 2. 配置邮件

在 GitHub 仓库设置 Secret：`Settings → Secrets and variables → Actions → New repository secret`

| Name              | Value                              |
| ----------------- | ---------------------------------- |
| `EMAIL_PASSWORD`  | QQ 邮箱 SMTP 授权码（非 QQ 密码）  |

> QQ 邮箱授权码获取：QQ 邮箱 → 设置 → 账户 → POP3/SMTP 服务 → 生成授权码

### 3. 定时运行

GitHub Actions 已配置每天北京时间 19:00（UTC 11:00）自动执行，也可在 Actions 页面手动触发（`workflow_dispatch`）。

### 4. 运行测试

```bash
uv run python -m unittest test_monitor -v
```

## 股票配置

编辑 `stocks.json` 中的 `stocks` 数组：

```json
{
  "name": "股票名称",
  "code": "股票代码（6位）",
  "trigger_price": 触发价格,
  "direction": "le",
  "triggered": false
}
```

- `code`：6 位数字股票代码，如 `000333`
- `trigger_price`：触发价格阈值
- `direction`：`"le"` = 当前价 ≤ 触发价时提醒；`"ge"` = 当前价 ≥ 触发价时提醒
- `triggered`：`false` = 待监控，触发后自动改为 `true`，下次跳过

### 添加股票

在 `stocks` 数组中新增条目即可。

### 删除股票

从 `stocks` 数组中移除对应条目。

### 重置已触发股票

```bash
uv run python reset_trigger.py
```

或手动将 `stocks.json` 中对应股票的 `triggered` 改回 `false`。

## 邮件配置

`stocks.json` 中 `email` 字段：

```json
{
  "email": {
    "sender": "786501105@qq.com",
    "receiver": "786501105@qq.com",
    "smtp_server": "smtp.qq.com",
    "smtp_port": 465
  }
}
```

密码通过环境变量 `EMAIL_PASSWORD` 传入，由 GitHub Secrets 提供。

## 技术栈

- Python 3.10+
- [腾讯行情接口](https://qt.gtimg.cn) — 主力数据源，批量获取实时行情
- [akshare](https://github.com/akfamily/akshare) — A 股行情备用数据源
- uv — 包管理
- GitHub Actions — 定时执行
