--!strict
-- Server bootstrap: builds the map and runs the Collect -> Sell -> Upgrade loop.
-- Every action comes from a server-side ProximityPrompt, so the client sends no
-- gameplay requests and has nothing to forge; clients only read player attributes.

local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")

local Economy = require(ReplicatedStorage.Shared.Economy)
local PlayerData = require(script.PlayerData)

local ACTION_COOLDOWN = 0.2

local states: { [Player]: Economy.State } = {}
local lastAction: { [Player]: number } = {}

local function publish(player: Player, state: Economy.State)
	player:SetAttribute("Cash", state.cash)
	player:SetAttribute("Carried", state.carried)
	player:SetAttribute("Level", state.level)
	player:SetAttribute("Capacity", Economy.capacity(state.level))
	player:SetAttribute("UpgradeCost", Economy.upgradeCost(state.level))
	local leaderstats = player:FindFirstChild("leaderstats")
	local cash = leaderstats and leaderstats:FindFirstChild("Cash")
	if cash and cash:IsA("IntValue") then
		cash.Value = state.cash
	end
end

local function makeStation(name: string, color: Color3, position: Vector3, actionText: string)
	local part = Instance.new("Part")
	part.Name = name
	part.Anchored = true
	part.Size = Vector3.new(8, 1, 8)
	part.Position = position
	part.Color = color
	part.Material = Enum.Material.SmoothPlastic
	part.Parent = workspace

	local prompt = Instance.new("ProximityPrompt")
	prompt.Name = name
	prompt.ActionText = actionText
	prompt.ObjectText = name
	prompt.HoldDuration = 0
	prompt.MaxActivationDistance = 12
	prompt.RequiresLineOfSight = false
	prompt.Parent = part
	return prompt
end

local function buildMap()
	local baseplate = Instance.new("Part")
	baseplate.Name = "Ground"
	baseplate.Anchored = true
	baseplate.Size = Vector3.new(120, 1, 120)
	baseplate.Position = Vector3.new(0, -0.5, 0)
	baseplate.Color = Color3.fromRGB(96, 160, 96)
	baseplate.Parent = workspace

	local spawn = Instance.new("SpawnLocation")
	spawn.Anchored = true
	spawn.Size = Vector3.new(6, 1, 6)
	spawn.Position = Vector3.new(0, 0.5, 0)
	spawn.Parent = workspace

	return {
		collect = makeStation(
			"Collect",
			Color3.fromRGB(240, 200, 60),
			Vector3.new(-20, 0.5, 0),
			"Collect"
		),
		sell = makeStation("Sell", Color3.fromRGB(60, 200, 90), Vector3.new(20, 0.5, 0), "Sell"),
		upgrade = makeStation(
			"Upgrade",
			Color3.fromRGB(80, 140, 240),
			Vector3.new(0, 0.5, 20),
			"Upgrade bag"
		),
	}
end

-- Rate limit per player so prompt spam cannot be used to flood the economy.
local function allowed(player: Player): boolean
	local now = os.clock()
	if now - (lastAction[player] or 0) < ACTION_COOLDOWN then
		return false
	end
	lastAction[player] = now
	return true
end

local function bind(prompt: ProximityPrompt, action: (Economy.State) -> ())
	prompt.Triggered:Connect(function(player: Player)
		local state = states[player]
		if state == nil or not allowed(player) then
			return
		end
		action(state)
		publish(player, state)
	end)
end

local stations = buildMap()
bind(stations.collect, function(state)
	Economy.collect(state)
end)
bind(stations.sell, function(state)
	Economy.sell(state)
end)
bind(stations.upgrade, function(state)
	Economy.upgrade(state)
end)

local function onPlayerAdded(player: Player)
	local leaderstats = Instance.new("Folder")
	leaderstats.Name = "leaderstats"
	local cash = Instance.new("IntValue")
	cash.Name = "Cash"
	cash.Parent = leaderstats
	leaderstats.Parent = player

	local state = PlayerData.load(player.UserId)
	states[player] = state
	publish(player, state)
	-- Contract with Forge's Studio health check: this player is fully loaded.
	player:SetAttribute("ForgeReady", true)
end

local function onPlayerRemoving(player: Player)
	local state = states[player]
	if state then
		PlayerData.save(player.UserId, state)
	end
	states[player] = nil
	lastAction[player] = nil
end

Players.PlayerAdded:Connect(onPlayerAdded)
Players.PlayerRemoving:Connect(onPlayerRemoving)
for _, player in Players:GetPlayers() do
	task.spawn(onPlayerAdded, player)
end

game:BindToClose(function()
	for player, state in states do
		PlayerData.save(player.UserId, state)
	end
end)
