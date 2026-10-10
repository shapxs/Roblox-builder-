--!strict
-- Leaderboard kit: ranking and display helpers (Studio is not needed).

local Leaderboard = require("../../src/shared/Kits/Leaderboard")

local tests: { [string]: () -> () } = {}

local function eq(actual: any, expected: any, label: string)
	if actual ~= expected then
		error(
			string.format("%s: expected %s, got %s", label, tostring(expected), tostring(actual)),
			2
		)
	end
end

local entries = {
	{ userId = 1, name = "Ava", value = 50 },
	{ userId = 2, name = "Ben", value = 120 },
	{ userId = 3, name = "Cy", value = 50 },
	{ userId = 4, name = "Di", value = 7 },
}

tests["top is highest first with stable ties"] = function()
	local top = Leaderboard.top(entries, 3)
	eq(#top, 3, "count")
	eq(top[1].name, "Ben", "first")
	eq(top[2].name, "Ava", "tie broken by name")
	eq(top[3].name, "Cy", "third")
	eq(#Leaderboard.top(entries, 10), 4, "n larger than list")
	eq(entries[1].name, "Ava", "input not reordered")
end

tests["rankOf shares ranks on ties"] = function()
	eq(Leaderboard.rankOf(entries, 2), 1, "Ben")
	eq(Leaderboard.rankOf(entries, 1), 2, "Ava")
	eq(Leaderboard.rankOf(entries, 3), 2, "Cy shares rank")
	eq(Leaderboard.rankOf(entries, 4), 4, "Di")
	eq(Leaderboard.rankOf(entries, 5), nil, "absent")
end

tests["duplicate display names retain distinct identities"] = function()
	local sameName = {
		{ userId = 8, name = "Same", value = 10 },
		{ userId = 9, name = "Same", value = 20 },
	}
	eq(Leaderboard.rankOf(sameName, 8), 2, "first user")
	eq(Leaderboard.rankOf(sameName, 9), 1, "second user")
end

tests["abbreviate large numbers"] = function()
	eq(Leaderboard.abbreviate(950), "950", "small")
	eq(Leaderboard.abbreviate(1000), "1K", "exact K")
	eq(Leaderboard.abbreviate(1250), "1.2K", "K")
	eq(Leaderboard.abbreviate(3400000), "3.4M", "M")
	eq(Leaderboard.abbreviate(-2500), "-2.5K", "negative")
end

return tests
