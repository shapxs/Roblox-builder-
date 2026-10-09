-- Controller-owned economy invariants for template-derived games.
-- Loads the game's Economy module from GAME_ROOT (default /workspace, the sandbox
-- mount) without requiring anything the game controls, then drives it with long
-- seeded random action sequences. Exits non-zero on any violation.
local fs = require("@lune/fs")
local luau = require("@lune/luau")
local process = require("@lune/process")

local root = process.env.GAME_ROOT or "/workspace"
local path = root .. "/src/shared/Economy.luau"
if not fs.isFile(path) then
	print("POLICY FAIL: required src/shared/Economy.luau is missing")
	process.exit(1)
end
local Economy = luau.load(fs.readFile(path), { debugName = "Economy" })()

local failures = 0
local function check(cond: boolean, message: string)
	if not cond then
		failures += 1
		print("POLICY FAIL: " .. message)
	end
end

-- Invariants that must hold after every action, for any sequence.
local function invariants(s, label: string)
	check(s.cash >= 0, label .. ": cash went negative")
	check(s.carried >= 0, label .. ": carried went negative")
	check(s.carried <= Economy.capacity(s.level), label .. ": carried exceeds capacity")
	check(s.level >= 1 and s.level <= Economy.Config.maxLevel, label .. ": level out of range")
	check(s.cash == math.floor(s.cash), label .. ": fractional cash")
end

-- Small deterministic LCG (Lune has no Roblox Random); same sequence every run.
local seed = 20261008
local function nextInt(lo: number, hi: number): number
	seed = (seed * 1103515245 + 12345) % 2147483648
	return lo + seed % (hi - lo + 1)
end

for run = 1, 200 do
	local s = Economy.newState()
	local value = 0 -- total value created, to check conservation
	local spent = 0
	for step = 1, 300 do
		local roll = nextInt(1, 3)
		local label = string.format("run %d step %d", run, step)
		if roll == 1 then
			Economy.collect(s)
		elseif roll == 2 then
			value += Economy.sell(s)
		else
			local level, cash = s.level, s.cash
			local ok = Economy.upgrade(s)
			if ok then
				check(s.level == level + 1, label .. ": upgrade did not raise level by 1")
				spent += cash - s.cash
			else
				check(s.level == level and s.cash == cash, label .. ": failed upgrade changed state")
			end
		end
		invariants(s, label)
	end
	check(s.cash == value - spent, string.format("run %d: cash not conserved", run))
end

-- Pacing: no level may demand an absurd grind.
for level = 1, Economy.Config.maxLevel - 1 do
	local trips = math.ceil(Economy.upgradeCost(level) / (Economy.capacity(level) * Economy.Config.resourceValue))
	check(trips <= 25, string.format("level %d needs %d full-bag trips (max 25)", level, trips))
end

-- Tampered saves always sanitize into a valid state.
for _, raw in { "x", 5, {}, { cash = -1, carried = 1e9, level = 0 / 0 }, { level = 99 } } do
	invariants(Economy.sanitize(raw), "sanitize")
end

print(string.format("policy: economy invariants %s", if failures == 0 then "PASS" else "FAIL"))
process.exit(if failures == 0 then 0 else 1)
