--!strict
-- Unlocks kit: progression rules (Studio is not needed).

local Unlocks = require("../../src/shared/Kits/Unlocks")

local tests: { [string]: () -> () } = {}

local function eq(actual: any, expected: any, label: string)
	if actual ~= expected then
		error(
			string.format("%s: expected %s, got %s", label, tostring(expected), tostring(actual)),
			2
		)
	end
end

local RULES = Unlocks.define({
	{ id = "rare_grove", level = 8, title = "Rare grove" },
	{ id = "glow_basket", level = 5, title = "Glowing basket" },
	{ id = "lantern", level = 5, title = "Lantern" },
})

tests["define sorts by level then id"] = function()
	eq(RULES[1].id, "glow_basket", "first")
	eq(RULES[2].id, "lantern", "tie by id")
	eq(RULES[3].id, "rare_grove", "last")
end

tests["define rejects bad rules"] = function()
	eq(
		pcall(
			Unlocks.define,
			{ { id = "a", level = 1, title = "A" }, { id = "a", level = 2, title = "B" } }
		),
		false,
		"duplicate"
	)
	eq(pcall(Unlocks.define, { { id = "a", level = 0, title = "A" } }), false, "level 0")
	eq(pcall(Unlocks.define, { { id = "a", level = 1.5, title = "A" } }), false, "fractional")
end

tests["newly reports only crossed unlocks"] = function()
	eq(#Unlocks.newly(RULES, 4, 5), 2, "two at level 5")
	eq(#Unlocks.newly(RULES, 5, 5), 0, "no change")
	eq(#Unlocks.newly(RULES, 1, 20), 3, "big jump")
	eq(#Unlocks.newly(RULES, 6, 3), 0, "level down")
end

tests["isUnlocked, unlockedAt and nextAfter"] = function()
	eq(Unlocks.isUnlocked(RULES, "rare_grove", 7), false, "locked")
	eq(Unlocks.isUnlocked(RULES, "rare_grove", 8), true, "unlocked")
	eq(Unlocks.isUnlocked(RULES, "missing", 99), false, "unknown")
	eq(#Unlocks.unlockedAt(RULES, 5), 2, "at 5")
	eq((Unlocks.nextAfter(RULES, 5) :: any).id, "rare_grove", "next")
	eq(Unlocks.nextAfter(RULES, 8), nil, "none left")
end

return tests
