# 股票价格提醒工具

通过 GitHub Actions 定时监控 A 股股价，当股价触及设定条件时发送 QQ 邮件通知。

## 项目结构

```
stock-monitor/
├── pyproject.toml                  # uv 项目配置，依赖 akshare
├── stocks.json                     # 股票监控列表 + 触发状态（运行时更新）
├── main.py                         # 核心监控脚本
├── reset_trigger.py               # 重置所有已触发股票状态
├── .github/workflows/monitor.yml  # GitHub Actions 定时任务（每晚 21:00 北京时间）
└── .gitignore
```

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

GitHub Actions 已配置每天北京时间 21:00（UTC 13:00）自动执行，也可在 Actions 页面手动触发（`workflow_dispatch`）。

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
- [akshare](https://github.com/akfamily/akshare) — A 股实时行情数据
- uv — 包管理
- GitHub Actions — 定时执行
