--!strict
-- Pure game-economy rules. No Roblox globals, so Lune can unit-test it headless.

export type State = {
	cash: number,
	carried: number,
	level: number,
}

local Economy = {}

Economy.Config = table.freeze({
	resourceValue = 1,
	baseCapacity = 10,
	capacityPerLevel = 10,
	baseUpgradeCost = 10,
	-- x1.35 per level keeps every level within ~12 full-bag trips (see pacing test);
	-- doubling made level 20 cost 2.6 million collections.
	upgradeCostGrowth = 1.35,
	maxLevel = 20,
})

function Economy.newState(): State
	return { cash = 0, carried = 0, level = 1 }
end

function Economy.capacity(level: number): number
	return Economy.Config.baseCapacity + (level - 1) * Economy.Config.capacityPerLevel
end

function Economy.upgradeCost(level: number): number
	return math.floor(
		Economy.Config.baseUpgradeCost * Economy.Config.upgradeCostGrowth ^ (level - 1)
	)
end

-- Full-bag trips needed to afford the next upgrade (pacing metric).
function Economy.tripsToUpgrade(level: number): number
	local perTrip = Economy.capacity(level) * Economy.Config.resourceValue
	return math.ceil(Economy.upgradeCost(level) / perTrip)
end

function Economy.collect(state: State): (boolean, string?)
	if state.carried >= Economy.capacity(state.level) then
		return false, "bag_full"
	end
	state.carried += 1
	return true, nil
end

function Economy.sell(state: State): number
	local earned = state.carried * Economy.Config.resourceValue
	state.cash += earned
	state.carried = 0
	return earned
end

function Economy.upgrade(state: State): (boolean, string?)
	if state.level >= Economy.Config.maxLevel then
		return false, "max_level"
	end
	local cost = Economy.upgradeCost(state.level)
	if state.cash < cost then
		return false, "insufficient_cash"
	end
	state.cash -= cost
	state.level += 1
	return true, nil
end

-- Repairs a loaded save so corrupted or tampered data can never break the economy.
function Economy.sanitize(raw: any): State
	local state = Economy.newState()
	if type(raw) ~= "table" then
		return state
	end
	local function whole(value: any, min: number, max: number, default: number): number
		if type(value) ~= "number" or value ~= value then
			return default
		end
		return math.clamp(math.floor(value), min, max)
	end
	state.level = whole(raw.level, 1, Economy.Config.maxLevel, 1)
	state.cash = whole(raw.cash, 0, 1e12, 0)
	state.carried = whole(raw.carried, 0, Economy.capacity(state.level), 0)
	return state
end

return Economy
