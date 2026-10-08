--!strict
-- Headless unit tests for the economy rules. Run with: lune run tests/run.luau

local Economy = require("../../src/shared/Economy")

local tests: { [string]: () -> () } = {}

local function eq(actual: any, expected: any, label: string)
	if actual ~= expected then
		error(
			string.format("%s: expected %s, got %s", label, tostring(expected), tostring(actual)),
			2
		)
	end
end

tests["collect fills the bag up to capacity"] = function()
	local s = Economy.newState()
	for _ = 1, Economy.capacity(1) do
		eq(Economy.collect(s), true, "collect")
	end
	local ok, reason = Economy.collect(s)
	eq(ok, false, "collect when full")
	eq(reason, "bag_full", "reason")
	eq(s.carried, Economy.capacity(1), "carried")
end

tests["sell converts carried resources to cash"] = function()
	local s = Economy.newState()
	Economy.collect(s)
	Economy.collect(s)
	eq(Economy.sell(s), 2, "earned")
	eq(s.cash, 2, "cash")
	eq(s.carried, 0, "carried")
end

tests["upgrade spends cash and raises capacity"] = function()
	local s = Economy.newState()
	s.cash = Economy.upgradeCost(1)
	eq(Economy.upgrade(s), true, "upgrade")
	eq(s.level, 2, "level")
	eq(s.cash, 0, "cash")
	eq(Economy.capacity(2) > Economy.capacity(1), true, "capacity grows")
end

tests["upgrade refuses without enough cash"] = function()
	local s = Economy.newState()
	local ok, reason = Economy.upgrade(s)
	eq(ok, false, "upgrade")
	eq(reason, "insufficient_cash", "reason")
	eq(s.level, 1, "level unchanged")
end

tests["sanitize repairs tampered saves"] = function()
	local s = Economy.sanitize({ cash = -50, carried = 9999, level = 0 / 0 })
	eq(s.cash, 0, "cash")
	eq(s.level, 1, "level")
	eq(s.carried, Economy.capacity(1), "carried clamped")
	eq(Economy.sanitize("garbage").level, 1, "non-table")
end

tests["every level is reachable in a bounded number of full-bag trips"] = function()
	eq(Economy.tripsToUpgrade(1), 1, "first upgrade after one full bag")
	for level = 1, Economy.Config.maxLevel - 1 do
		if Economy.tripsToUpgrade(level) > 15 then
			error(string.format("level %d needs %d trips", level, Economy.tripsToUpgrade(level)))
		end
	end
end

return tests
