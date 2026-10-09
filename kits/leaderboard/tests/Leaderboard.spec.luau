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
	{ name = "Ava", value = 50 },
	{ name = "Ben", value = 120 },
	{ name = "Cy", value = 50 },
	{ name = "Di", value = 7 },
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
	eq(Leaderboard.rankOf(entries, "Ben"), 1, "Ben")
	eq(Leaderboard.rankOf(entries, "Ava"), 2, "Ava")
	eq(Leaderboard.rankOf(entries, "Cy"), 2, "Cy shares rank")
	eq(Leaderboard.rankOf(entries, "Di"), 4, "Di")
	eq(Leaderboard.rankOf(entries, "Zed"), nil, "absent")
end

tests["abbreviate large numbers"] = function()
	eq(Leaderboard.abbreviate(950), "950", "small")
	eq(Leaderboard.abbreviate(1000), "1K", "exact K")
	eq(Leaderboard.abbreviate(1250), "1.2K", "K")
	eq(Leaderboard.abbreviate(3400000), "3.4M", "M")
	eq(Leaderboard.abbreviate(-2500), "-2.5K", "negative")
end

return tests
