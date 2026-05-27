# BA Monitor Kirisame

断箭 QQ 游戏数据分析助手。目标是做成类似 Kokomi 的查询机器人：用户在 QQ 单聊、群聊或频道里输入指令，机器人调用断箭数据 API，返回玩家、单位、版本环境和对局分析。

## 当前状态

这是 Sprint 0 骨架，已经包含：

- QQ 官方机器人 SDK 接入入口。
- 命令解析和帮助文本。
- 游戏数据 Provider 抽象，默认使用 BArmory STB 数据源，Mock 数据兜底。
- 玩家摘要、近期对局、单场对局、环境摘要、单位摘要的第一版输出。
- 单元测试。

## 数据源决策

第一版采用 BArmory STB API：

- 它已经能提供玩家 Profile、ELO、排名、胜率、K/D、近期对局 ID 和单场对局详情。
- 它比纯网页解析稳定，也比只用 BA Hub GraphQL 更适合做“玩家近期战绩/单场复盘”。
- 它不是官方 API，所以必须加缓存、限流和错误降级；后续如果拿到官方 API，只替换 Provider 层。

数据源优先级：

1. BArmory STB：玩家、近期对局、单场对局。
2. BA Hub GraphQL：后续补全全局环境、单位表现、趋势图。
3. Mock：本地开发、接口不可用时兜底。

## QQ 接入流程

1. 前往 [QQ 开放平台](https://q.qq.com/) 注册开发者并创建机器人。
2. 在机器人管理端获取 `AppID` 和 `AppSecret`。
3. 配置沙箱群、沙箱单聊或沙箱频道，用于上线前测试。
4. 按需要配置事件订阅。群聊需要关注 `GROUP_AT_MESSAGE_CREATE`，单聊需要关注 `C2C_MESSAGE_CREATE`，频道 @ 需要关注 `AT_MESSAGE_CREATE`。
5. 正式环境按平台要求配置 IP 白名单；如果消息里包含 URL，还要配置消息 URL 白名单。
6. 审核通过后上线，再把机器人添加到目标 QQ 场景。

## 本地运行

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

填写 `.env` 后运行：

```powershell
python -m ba_monitor
```

## 指令

```text
/help
/bind <SteamID>
/me
/player [SteamID]
/recent [SteamID]
/match <对局ID>
/meta
/unit <单位名>
```

绑定账号后，`/me`、`/player`、`/recent` 可以不填写 SteamID，机器人会默认查询当前 QQ 用户绑定的账号。

## 测试

```powershell
pytest
```

## 数据 API 替换点

后续拿到断箭官方 API 文档后，优先修改 `src/ba_monitor/providers.py` 里的 Provider，保持 `GameDataProvider` 接口不变。
