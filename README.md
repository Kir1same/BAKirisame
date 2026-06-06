# BA Monitor Kirisame

BA Monitor Kirisame 是一个面向《Broken Arrow / 断箭》玩家的 QQ 游戏数据查询与可视化机器人。

当前版本是第一版测试交付，核心目标是让 QQ 用户通过指令查询玩家战绩、近期表现、排名位置和服务器状态，并以图片卡片的形式返回结果。项目目前使用 BArmory STB、BATrace 与 Steam 公开数据接口作为数据来源。

## 当前状态

版本：`v0.1` 测试版

已完成并可用于测试的能力：

- QQ 官方机器人 SDK 接入，支持 C2C 私聊与群聊场景。
- 玩家绑定与解绑。
- 玩家名、玩家 ID、SteamID64 查询。
- `/me` 玩家综合数据卡片。
- `/player` 指定玩家数据卡片。
- `/recent` 近期战绩卡片。
- `/rank` 全服排名分布卡片。
- `/serverCondition` 当前服务器运行状态卡片。
- `/help` 静态帮助图。
- 图片卡片生成与公网静态托管。
- 机器人日志与 QQ 消息日志，日志按时间裁剪，避免长期膨胀。

## 指令

```text
/help
/bind <SteamID64|玩家ID|玩家名>
/unbind
/me
/player <SteamID64|玩家ID|玩家名>
/rank
/rank <SteamID64|玩家ID|玩家名>
/recent
/recent <天数>
/recent <天数> <SteamID64|玩家ID|玩家名>
/serverCondition
```

说明：

- `/me`、`/recent`、`/rank` 在没有额外参数时，会使用当前 QQ 用户已绑定的账号。
- `/player` 必须提供查询目标。
- `/recent` 的天数范围建议为 `1-30`。
- `/help` 会优先返回预生成的帮助图片。

## 数据来源

当前第一版使用以下数据来源：

- BArmory STB：玩家资料、ELO、排名、胜率、近期有效对局与单位样本。
- BATrace：玩家搜索、短 ID 解析、服务器状态与全服分布数据。
- Steam：服务器在线人数兜底数据。

需要注意：

- 这些并非《断箭》官方完整 API。
- 生涯数据目前主要依赖可获得的总场次、总胜率、ELO 与排名。
- 近期对局、单位表现、服务器细分状态来自第三方公开接口，接口不可用或缓存异常时会自动降级。
- 卡片中的“测试版”标识表示数据和评价模型仍处于迭代阶段。

## 本地运行

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -U pip
pip install -e .
Copy-Item .env.example .env
```

填写 `.env` 后运行：

```powershell
python -m ba_monitor
```

## 环境变量

复制 `.env.example` 为 `.env`：

```env
QQ_APP_ID=
QQ_APP_SECRET=
QQ_SANDBOX=true

DATA_SOURCE=barmory
BA_API_BASE_URL=https://barmory.net
BA_API_KEY=

IMAGE_PUBLIC_BASE_URL=
IMAGE_PUBLIC_DIR=artifacts/public/cards

LOG_LEVEL=INFO
```

关键配置：

- `QQ_APP_ID`：QQ 机器人 AppID。
- `QQ_APP_SECRET`：QQ 机器人 AppSecret。
- `QQ_SANDBOX`：沙箱测试阶段为 `true`，正式环境改为 `false`。
- `IMAGE_PUBLIC_BASE_URL`：QQ 可以访问到的图片公网地址，例如 `http://服务器公网IP:8010/cards`。
- `IMAGE_PUBLIC_DIR`：图片实际保存目录，默认 `artifacts/public/cards`。

## 图片服务

机器人会把生成的 PNG 卡片保存到 `IMAGE_PUBLIC_DIR`，再把 `IMAGE_PUBLIC_BASE_URL/文件名` 提交给 QQ 富媒体接口。

本地或服务器上可以用 Python 静态服务托管：

```bash
mkdir -p artifacts/public/cards
python -m http.server 8010 --directory artifacts/public
```

测试：

```bash
curl -I http://127.0.0.1:8010/cards/help.png
```

生产或长期测试建议使用：

- 阿里云轻量应用服务器。
- `systemd` 常驻 bot 与图片服务。
- 公网 IP + 安全组开放图片端口，或 Nginx + 域名 + HTTPS。

## 阿里云部署参考

推荐第一版测试配置：

- 2 vCPU
- 2 GiB 内存
- Ubuntu 22.04 LTS
- 40GB 或以上系统盘
- 开放 SSH 端口。
- 如直接使用 Python 静态图片服务，需要额外开放 `8010/TCP`。

安装依赖：

```bash
sudo apt update
sudo apt install -y git python3 python3-venv python3-pip curl unzip fonts-noto-cjk fonts-wqy-microhei fonts-wqy-zenhei
```

拉取项目：

```bash
git clone https://github.com/Kir1same/BAKirisame.git
cd BAKirisame
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -e .
```

创建 `.env` 后，可以先手动启动：

```bash
python -m ba_monitor
```

## systemd 常驻服务

图片服务示例：

```ini
[Unit]
Description=BA Monitor image static server
After=network.target

[Service]
Type=simple
WorkingDirectory=/root/BAKirisame
ExecStart=/root/BAKirisame/.venv/bin/python -m http.server 8010 --directory artifacts/public
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

机器人服务示例：

```ini
[Unit]
Description=BA Monitor QQ bot
After=network.target ba-image.service
Wants=ba-image.service

[Service]
Type=simple
WorkingDirectory=/root/BAKirisame
Environment=PYTHONUNBUFFERED=1
ExecStart=/root/BAKirisame/.venv/bin/python -m ba_monitor
Restart=always
RestartSec=8

[Install]
WantedBy=multi-user.target
```

如果部署用户不是 `root`，需要把路径改成实际项目目录，例如 `/home/ubuntu/BAKirisame`。

启用服务：

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now ba-image
sudo systemctl enable --now ba-bot
```

查看日志：

```bash
sudo journalctl -u ba-bot -f
```

## 测试

```powershell
pytest
```

或：

```bash
python -m pytest
```

## 当前限制

- 这是测试版机器人，不应作为官方数据源或最终评价标准。
- PR 与评价模型仍在迭代，公式暂不公开。
- 第三方接口可能存在缓存、字段变化或临时不可用。
- 服务器状态细分数据优先使用 BATrace，失败时会降级到 Steam 在线人数。
- 图片发送依赖公网图片地址，`IMAGE_PUBLIC_BASE_URL` 配置错误时会回退为文字回复。

## 项目结构

```text
src/ba_monitor/
  bot.py          QQ 机器人入口与消息处理
  commands.py     指令解析
  providers.py    数据源接入与转换
  cards.py        图片卡片生成
  image_host.py   图片发布路径处理
  config.py       环境变量配置
tests/            单元测试
scripts/          静态资源生成脚本
artifacts/        本地生成的图片与测试产物
```

## 后续计划

- 完善 QQ 正式审核所需说明与自测报告。
- 稳定域名与 HTTPS 图片托管。
- 继续修正地图映射和单位名称映射。
- 增加更多全服统计卡片。
- 根据真实玩家反馈继续调整 PR 与卡片视觉设计。
