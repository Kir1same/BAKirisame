# BArmory STB API 调研

调研日期：2026-05-27

## 结论

BArmory.net 暴露了一组社区 STB 数据接口，可用于断箭玩家统计、排行榜、近期对局和对局详情查询。它不是游戏官方 API，因此项目里应把它作为可替换的数据源，并加入缓存、限流和错误降级。

## 请求流程

先获取 attestation token：

```http
POST https://barmory.net/gateway/attest
Content-Type: application/json
Accept: application/json
X-Barmory-ID: <client-uuid>
X-Type: BEZ
X-Barmory-Version: 6

{}
```

响应：

```json
{
  "token": "...",
  "expiresAt": 1779912594
}
```

后续 STB 请求需要携带：

```http
Accept: application/json
Content-Type: application/json
X-Barmory-ID: <same-client-uuid>
X-Type: stb
X-Barmory-Version: 6
X-Barmory-Attest: <token>
```

## 已验证接口

### 玩家 STB Profile

```http
GET https://barmory.net/stb/commander/{steamId}/steam?time={cacheKey}
```

示例：

```http
GET /stb/commander/76561198157609957/steam?time=2026-05-27
```

返回字段包含：

- `id`：BArmory/STB 内部 commander id，后续查 matches 用这个。
- `name`
- `steamId`
- `lvl`
- `rt`：ELO/rating。
- `rk`：排行榜名次。
- `rtgms`：rated games。

### 玩家统计

```http
GET https://barmory.net/stb/commander/{steamId}/stats?time={cacheKey}
```

返回字段包含：

- `statisticByLobbyType.Rating.fightsCount`
- `statisticByLobbyType.Rating.winsCount`
- `statisticByLobbyType.Rating.losesCount`
- `statisticByLobbyType.Rating.leavesCount`
- `statisticByLobbyType.Rating.kdRatio`
- `capturedZonesCount`
- `mapsPlayCount`
- `updateDate`

### 玩家近期对局列表

```http
GET https://barmory.net/stb/commander/{stbCommanderId}/matches?time={cacheKey}
```

注意：这里用的是 Profile 返回的 `id`，不是 Steam ID。

返回：

```json
[5545812, 5509204, 5603924]
```

### 单场对局详情

```http
GET https://barmory.net/stb/match/{matchId}
```

返回字段包含：

- `TotalObjectiveZonesCount`
- `MapId`
- `EndTime`
- `TotalPlayTimeInSec`
- `WinnerTeam`
- `Data`：按玩家 id 分组的对局表现。

`Data` 内玩家字段常见有：

- `Id`
- `Name`
- `TeamId`
- `OldRating`
- `NewRating`
- `TotalSpawnedUnitScore`
- `TotalRefundedUnitScore`
- `DamageDealt`
- `DamageReceived`
- `Destruction`
- `Losses`
- `ObjectivesCaptured`
- `SupplyPointsConsumed`
- `UnitData`

### 批量对局详情

```http
POST https://barmory.net/stb/matches
```

请求体：

```json
[5545812, 5509204]
```

返回是字符串数组，每个元素是一场对局的 JSON 字符串，需要再 `json.loads` 一次。

## 待确认

- `GET /stb/leaderboard` 当前直接请求返回 404；前端仍有调用代码，可能路径、缓存键或访问条件不同。
- BArmory 是否允许第三方机器人长期调用，需要联系站点作者确认。
- 高频群聊查询必须缓存，建议玩家 profile/stats 缓存 10-30 分钟，对局详情长期缓存。

## 项目接入建议

第一阶段只做：

- `/player <steamId>`：profile + stats。
- `/recent <steamId>`：最近 5 场摘要。
- `/match <matchId>`：单场简报。

暂缓：

- 全服排行榜。
- 批量爬取。
- 自动刷新全量 meta。

