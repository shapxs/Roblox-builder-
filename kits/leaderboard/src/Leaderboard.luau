--!strict
-- Leaderboard kit: player-list stats (leaderstats) plus pure ranking helpers for
-- in-world boards or HUD "top players" panels. Server-side; values are set only by
-- the server, so clients can never write them.
--
--   local Leaderboard = require(ReplicatedStorage.Shared.Kits.Leaderboard)
--   Leaderboard.define(player, { "Cash", "Mushrooms" })   -- on PlayerAdded
--   Leaderboard.set(player, "Mushrooms", total)
--   local top = Leaderboard.top(Leaderboard.snapshot(Players:GetPlayers(), "Mushrooms"), 5)

export type Entry = { userId: number, name: string, value: number }

local Leaderboard = {}

local MAX_STATS = 4 -- the Roblox player list shows at most four

local function folder(player: Player): Folder
	local existing = player:FindFirstChild("leaderstats")
	if existing and existing:IsA("Folder") then
		return existing
	end
	local created = Instance.new("Folder")
	created.Name = "leaderstats"
	created.Parent = player
	return created
end

-- Create the named stats (in display order) if missing. Existing stats are kept.
function Leaderboard.define(player: Player, stats: { string })
	assert(#stats >= 1 and #stats <= MAX_STATS, "define 1 to 4 stats")
	local f = folder(player)
	for _, name in stats do
		if f:FindFirstChild(name) == nil then
			local value = Instance.new("IntValue")
			value.Name = name
			value.Parent = f
		end
	end
end

function Leaderboard.set(player: Player, stat: string, value: number)
	local f = player:FindFirstChild("leaderstats")
	local v = f and f:FindFirstChild(stat)
	if v and v:IsA("IntValue") then
		v.Value = math.floor(value)
	end
end

function Leaderboard.get(player: Player, stat: string): number
	local f = player:FindFirstChild("leaderstats")
	local v = f and f:FindFirstChild(stat)
	return if v and v:IsA("IntValue") then v.Value else 0
end

function Leaderboard.snapshot(players: { Player }, stat: string): { Entry }
	local entries: { Entry } = {}
	for _, player in players do
		table.insert(entries, {
			userId = player.UserId,
			name = player.DisplayName,
			value = Leaderboard.get(player, stat),
		})
	end
	return entries
end

-- Highest first; ties broken by unique user ID so the order is stable.
function Leaderboard.top(entries: { Entry }, n: number): { Entry }
	local sorted = table.clone(entries)
	table.sort(sorted, function(a: Entry, b: Entry): boolean
		if a.value ~= b.value then
			return a.value > b.value
		end
		return a.userId < b.userId
	end)
	local out: { Entry } = {}
	for i = 1, math.min(n, #sorted) do
		out[i] = sorted[i]
	end
	return out
end

-- 1-based rank of a user ID in `entries` (ties share a rank), or nil if absent.
function Leaderboard.rankOf(entries: { Entry }, userId: number): number?
	local mine: number? = nil
	for _, e in entries do
		if e.userId == userId then
			mine = e.value
		end
	end
	if mine == nil then
		return nil
	end
	local rank = 1
	for _, e in entries do
		if e.value > mine then
			rank += 1
		end
	end
	return rank
end

local UNITS: { { size: number, suffix: string } } = {
	{ size = 1e9, suffix = "B" },
	{ size = 1e6, suffix = "M" },
	{ size = 1e3, suffix = "K" },
}

-- Short display text: 950, 1.2K, 3.4M, 1.1B.
function Leaderboard.abbreviate(value: number): string
	local abs = math.abs(value)
	local sign = if value < 0 then "-" else ""
	for _, unit in UNITS do
		if abs >= unit.size then
			local scaled = math.floor(abs / unit.size * 10) / 10
			local text = if scaled == math.floor(scaled)
				then string.format("%d", scaled)
				else string.format("%.1f", scaled)
			return sign .. text .. unit.suffix
		end
	end
	return sign .. tostring(math.floor(abs))
end

return Leaderboard
