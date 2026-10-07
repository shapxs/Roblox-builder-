```lua
-- GameManager.server.lua

local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local DataStoreService = game:GetService("DataStoreService")
local HttpService = game:GetService("HttpService")

-- Create Events folder if it doesn't exist
local eventsFolder = ReplicatedStorage:FindFirstChild("Events")
if not eventsFolder then
	eventsFolder = Instance.new("Folder")
	eventsFolder.Name = "Events"
	eventsFolder.Parent = ReplicatedStorage
end

-- Create RemoteEvents
local gameStartedEvent = eventsFolder:FindFirstChild("GameStarted")
if not gameStartedEvent then
	gameStartedEvent = Instance.new("RemoteEvent")
	gameStartedEvent.Name = "GameStarted"
	gameStartedEvent.Parent = eventsFolder
end

local playerJoinedEvent = eventsStartedEvent:FindFirstChild("PlayerJoined")
if not playerJoinedEvent then
	playerJoinedEvent = Instance.new("RemoteEvent")
	playerJoinedEvent.Name = "PlayerJoined"
	playerJoinedEvent.Parent = eventsFolder
end

local playerLeftEvent = eventsFolder:FindFirstChild("PlayerLeft")
if not playerLeftEvent then
	playerLeftEvent = Instance.new("RemoteEvent")
	playerLeftEvent.Name = "PlayerLeft"
	playerLeftEvent.Parent = eventsFolder
end

-- DataStore for player data
local playerDataStore = DataStoreService:GetDataStore("TestTycoon_PlayerData")

-- Global game state
local gameState = {
	IsRunning = false,
	Players = {},
	MiningBases = {}, -- { [player] = basePart }
}

-- Helper: Generate unique key per player
local function getPlayerKey(player)
	return "player_" .. player.UserId
end

-- Load player data from DataStore
local function loadPlayerData(player)
	local success, data = pcall(function()
		return playerDataStore:GetAsync(getPlayerKey(player))
	end)

	if not success then
		warn("Failed to load data for player", player.Name, ":", data)
		data = nil
	end

	if not data or type(data) ~= "table" then
		data = {
			MiningCredits = 0,
			MinersBuilt = 0,
			LastLogin = os.time(),
		}
	end

	return data
end

-- Save player data to DataStore
local function savePlayerData(player, data)
	local success, err = pcall(function()
		playerDataStore:SetAsync(getPlayerKey(player), data)
	end)

	if not success then
		warn("Failed to save data for player", player.Name, ":", err)
	end
end

-- Initialize mining base for a player
local function createMiningBase(player)
	local baseFolder = Instance.new("Folder")
	baseFolder.Name = "MiningBase"
	baseFolder.Parent = workspace

	local basePart = Instance.new("Part")
	basePart.Name = "BasePlatform"
	basePart.Size = Vector3.new(10, 2, 10)
	basePart.Color = Color3.fromRGB(50, 150, 255)
	basePart.Anchored = true
	basePart.CanCollide = true
	basePart.Position = Vector3.new(
		math.random(-40, 40),
		2,
		math.random(-40, 40)
	)
	basePart.Parent = baseFolder

	local miningStation = Instance.new("Part")
	miningStation.Name = "MiningStation"
	miningStation.Size = Vector3.new(6, 1, 6)
	miningStation.Color = Color3.fromRGB(255, 200, 50)
	miningStation.Anchored = true
	miningStation.CanCollide = false
	miningStation.CFrame = basePart.CFrame * CFrame.new(0, 2, 0)
	miningStation.Parent = baseFolder

	-- Add mining resource nearby (asteroid cluster)
	for i = 1, 5 do
		local asteroid = Instance.new("Part")
		asteroid.Name = "Asteroid_" .. i
		asteroid.Size = Vector3.new(4 + math.random(), 4 + math.random(), 4 + math.random())
		asteroid.Color = Color3.fromRGB(150, 150, 150)
		asteroid.Anchored = true
		asteroid.CanCollide = false
		asteroid.CFrame = basePart.CFrame * CFrame.new(
			math.random(-20, 20),
			math.random(5, 15),
			math.random(-20, 20)
		)
		asteroid.Parent = workspace

		-- Tag asteroid for mining
		asteroid:SetAttribute("ResourceType", "SpaceOre")
		asteroid:SetAttribute("Value", math.random(5, 20))
	end

	return basePart
end

-- Player added event
Players.PlayerAdded:Connect(function(player)
	local character = player.Character or player.CharacterAdded:Wait()
	if not character then return end

	-- Load data
	local playerData = loadPlayerData(player)

	-- Initialize mining base if first time or no base exists
	if not gameState.MiningBases[player] then
		gameState.MiningBases[player] = createMiningBase(player)
	end

	-- Store player data in global state
	table.insert(gameState.Players, {
		Player = player,
		Data = playerData,
	})

	-- Fire remote event to client
	playerJoinedEvent:FireClient(player, playerData)

	-- Character added (for mining logic setup)
	character.ChildAdded:Connect(function(child)
		if child:IsA("Tool") then
			child.Activated:Connect(function()
				local hit = player:GetMouse().Hit.Position
				local parts = workspace:GetPartsInPart(
					Instance.new("Part", nil, {
						Size = Vector3.new(10, 10, 10),
						CFrame = CFrame.new(hit),
						Name = "TempHitbox",
					})
				)

				for _, part in ipairs(parts) do
					if part:GetAttribute("ResourceType") == "SpaceOre" then
						local oreValue = part:GetAttribute("Value")
						if type(oreValue) == "number" and oreValue > 0 then
							playerData.MiningCredits = (playerData.MiningCredits or 0) + oreValue

							-- Destroy asteroid
							part:Destroy()

							-- Save updated data immediately for mining action
							savePlayerData(player, playerData)

							break
						end
					end
				end
			end)
		end
	end)

	-- Handle disconnection
	local connection
	connection = player.CharacterAdded:Connect(function()
		character = player.Character or character
		if connection then connection:Disconnect() end
	end)

	player.CharacterRemoving:Connect(function(char)
		char:Destroy()
	end)

	player.CharacterAdded:Wait()

	-- Save data on disconnect
	player.Leaved:Connect(function()
		savePlayerData(player, playerData)
		table.remove(gameState.Players, function(p) return p.Player == player end)
		if gameState.MiningBases[player] then
			gameState.MiningBases[player]:Destroy()
			gameState.MiningBases[player] = nil
		end
		playerLeftEvent:FireAllClients(player.UserId)
	end)
end)

-- Game start logic (triggered by admin or after countdown)
local function startGame()
	if gameState.IsRunning then return end

	gameState.IsRunning = true

	-- Fire game started event to all clients
	gameStartedEvent:FireAllClients()

	-- Start mining resource regeneration loop
	spawn(function()
		while gameState.IsRunning do
			wait(60) -- 1 minute interval

			for _, playerEntry in ipairs(gameState.Players) do
				local player = playerEntry.Player
				if player and player:IsDescendantOf(Players) then
					-- Regenerate some asteroids near base
					local basePart = gameState.MiningBases[player]
					if basePart and basePart.Parent then
						for i = 1, math.random(2, 4) do
							local asteroid = Instance.new("Part")
							asteroid.Name = "Asteroid_" .. os.time() .. "_" .. i
							asteroid.Size = Vector3.new(4 + math.random(), 4 + math.random(), 4 + math.random())
							asteroid.Color = Color3.fromRGB(150, 150, 150)
							asteroid.Anchored = true
							asteroid.CanCollide = false
							asteroid.CFrame = basePart.CFrame * CFrame.new(
								math.random(-20, 20),
								math.random(5, 15),
								math.random(-20, 20)
							)
							asteroid.Parent = workspace

							asteroid:SetAttribute("ResourceType", "SpaceOre")
							asteroid:SetAttribute("Value", math.random(5, 20))
						end
					end
				end
			end
		end
	end)

	print("Test Tycoon game started!")
end

-- Expose startGame function to Admins via RemoteEvent (optional)
local adminStartEvent = Instance.new("RemoteEvent")
adminStartEvent.Name = "AdminStartGame"
adminStartEvent.Parent = ReplicatedStorage

adminStartEvent.OnServerEvent:Connect(function(player)
	if player:IsInGroup(123456) then -- Replace with your group ID for admins
		startGame()
	else
		warn("Unauthorized attempt to start game by", player.Name)
	end
end)

-- Auto-start after 5 seconds (for testing/demo purposes)
spawn(function()
	wait(5)
	if not gameState.IsRunning then
		startGame()
	end
end)

-- Save all players' data on game shutdown
game:BindToClose(function()
	for _, entry in ipairs(gameState.Players) do
		local player = entry.Player
		if player and player:IsDescendantOf(Players) then
			savePlayerData(player, entry.Data)
		end
	end

	print("Test Tycoon saved all player data.")
end)

-- Initial setup for existing players (in case of server restart)
for _, player in ipairs(Players:GetPlayers()) do
	local character = player.Character or player.CharacterAdded:Wait()
	if not character then continue end

	local playerData = loadPlayerData(player)

	if not gameState.MiningBases[player] then
		gameState.MiningBases[player] = createMiningBase(player)
	end

	table.insert(gameState.Players, {
		Player = player,
		Data = playerData,
	})

	playerJoinedEvent:FireClient(player, playerData)
end
```