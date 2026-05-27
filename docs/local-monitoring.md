# 本地监控

## 查看机器人进程

```powershell
Get-Process python
```

## 查看运行日志

```powershell
Get-Content .\logs\app.log -Encoding UTF8 -Wait -Tail 80
```

## 查看 QQ 聊天记录

```powershell
Get-Content .\logs\qq_messages.log -Encoding UTF8 -Wait -Tail 80
```

`qq_messages.log` 是 JSON Lines 格式，一行一条记录。

日志只保留最近 24 小时。机器人启动时会清理一次，运行中每小时自动清理一次。

字段说明：

- `direction`: `incoming` 表示 QQ 用户消息，`outgoing` 表示机器人回复。
- `scene`: `c2c`、`group`、`channel` 或测试场景。
- `message_id`: QQ 原始消息 ID。
- `reply_to_message_id`: 机器人回复对应的原始消息 ID。
- `content`: 消息内容。
- `author`: 发送者信息。
- `group_openid`、`guild_id`、`channel_id`: QQ 场景标识。

## 停止机器人

先查 PID：

```powershell
Get-Process python
```

再停止：

```powershell
Stop-Process -Id <PID>
```

## 启动机器人

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\start_bot.ps1
```
