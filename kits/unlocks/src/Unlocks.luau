--!strict
-- Unlocks kit: qualitative progression ("at level 5 the basket glows and rare
-- mushrooms appear"). Unlock rules are plain data; the logic is pure and
-- unit-tested; `applyWorld` shows/hides world content tagged for an unlock.
--
--   local Unlocks = require(ReplicatedStorage.Shared.Kits.Unlocks)
--   local RULES = Unlocks.define({
--       { id = "glow_basket", level = 5, title = "Glowing basket" },
--       { id = "rare_grove", level = 8, title = "Rare grove" },
--   })
--   for _, u in Unlocks.newly(RULES, oldLevel, newLevel) do ... announce u.title ... end
--   Unlocks.applyWorld(workspace, RULES, level)  -- parts with attribute Unlock = "rare_grove"

export type Rule = { id: string, level: number, title: string }

local Unlocks = {}

-- Validate and sort rules by level (ids unique, levels positive integers).
function Unlocks.define(rules: { Rule }): { Rule }
	local seen: { [string]: boolean } = {}
	for _, rule in rules do
		assert(type(rule.id) == "string" and rule.id ~= "", "unlock needs an id")
		assert(not seen[rule.id], "duplicate unlock id " .. rule.id)
		assert(rule.level >= 1 and rule.level == math.floor(rule.level), "bad level " .. rule.id)
		seen[rule.id] = true
	end
	local sorted = table.clone(rules)
	table.sort(sorted, function(a: Rule, b: Rule): boolean
		if a.level ~= b.level then
			return a.level < b.level
		end
		return a.id < b.id
	end)
	return table.freeze(sorted)
end

function Unlocks.isUnlocked(rules: { Rule }, id: string, level: number): boolean
	for _, rule in rules do
		if rule.id == id then
			return level >= rule.level
		end
	end
	return false
end

function Unlocks.unlockedAt(rules: { Rule }, level: number): { Rule }
	local out: { Rule } = {}
	for _, rule in rules do
		if level >= rule.level then
			table.insert(out, rule)
		end
	end
	return out
end

-- Rules crossed when going from oldLevel to newLevel (empty if not levelling up).
function Unlocks.newly(rules: { Rule }, oldLevel: number, newLevel: number): { Rule }
	local out: { Rule } = {}
	for _, rule in rules do
		if rule.level > oldLevel and rule.level <= newLevel then
			table.insert(out, rule)
		end
	end
	return out
end

-- The next locked rule above `level`, for "Next unlock at level 8: Rare grove" text.
function Unlocks.nextAfter(rules: { Rule }, level: number): Rule?
	for _, rule in rules do
		if rule.level > level then
			return rule
		end
	end
	return nil
end

-- Show content for reached unlocks and hide the rest: any BasePart / Model under
-- `root` with string attribute `Unlock` = rule id. Hidden parts are also made
-- non-collidable so locked areas cannot be walked into.
function Unlocks.applyWorld(root: Instance, rules: { Rule }, level: number)
	for _, item in root:GetDescendants() do
		local id = item:GetAttribute("Unlock")
		if type(id) == "string" then
			local open = Unlocks.isUnlocked(rules, id, level)
			local parts: { BasePart } = {}
			if item:IsA("BasePart") then
				table.insert(parts, item)
			end
			for _, child in item:GetDescendants() do
				if child:IsA("BasePart") then
					table.insert(parts, child)
				end
			end
			for _, part in parts do
				part.Transparency = if open
					then (part:GetAttribute("OpenTransparency") or 0) :: number
					else 1
				part.CanCollide = open and (part:GetAttribute("OpenCollide") ~= false)
			end
		end
	end
end

return Unlocks
