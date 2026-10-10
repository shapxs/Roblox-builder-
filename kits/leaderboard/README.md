# leaderboard kit

Player-list stats (leaderstats) set only by the server, plus ranking helpers and number abbreviation for in-world boards and HUD panels.

Module: `ReplicatedStorage.Shared.Kits.Leaderboard`

```lua
Leaderboard.define(player, {"Cash", "Mushrooms"})  -- on PlayerAdded, up to 4 stats
Leaderboard.set(player, stat, value) / Leaderboard.get(player, stat)
Leaderboard.top(Leaderboard.snapshot(Players:GetPlayers(), stat), 5) -> {userId, name, value}[]
Leaderboard.rankOf(entries, userId); Leaderboard.abbreviate(1250) -> "1.2K"
```
