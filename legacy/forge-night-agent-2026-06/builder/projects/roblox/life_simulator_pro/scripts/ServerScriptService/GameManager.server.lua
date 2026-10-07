-- GameManager.server.lua
-- Core game loop and state management

local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local DataStoreService = game:GetService("DataStoreService")

-- Load shared modules
local GameConfig = require(ReplicatedStorage:WaitForChild("GameConfig"))
local PlayerLib = require(ReplicatedStorage.Modules:WaitForChild("PlayerLib"))

-- Create Events folder and RemoteEvents if they don't exist
local EventsFolder = ReplicatedStorage:FindFirstChild("Events")
if not EventsFolder then
    EventsFolder = Instance.new("Folder")
    EventsFolder.Name = "Events"
    EventsFolder.Parent = ReplicatedStorage
    
    -- Create RemoteEvents
    local GameStartedEvent = Instance.new("RemoteEvent")
    GameStartedEvent.Name = "GameStarted"
    GameStartedEvent.Parent = EventsFolder
    
    local PlayerJoinedEvent = Instance.new("RemoteEvent")
    PlayerJoinedEvent.Name = "PlayerJoined"
    PlayerJoinedEvent.Parent = EventsFolder
    
    local PlayerLeftEvent = Instance.new("RemoteEvent")
    PlayerLeftEvent.Name = "PlayerLeft"
    PlayerLeftEvent.Parent = EventsFolder
end

-- Game state
local GameState = {
    IsRunning = false,
    ActivePlayers = {},
    StartTime = nil,
    EndTime = nil
}

-- Player data storage
local PlayerDataStore = DataStoreService:GetDataStore("PlayerData_" .. GameConfig.GameName)

-- Events
local GameStartedEvent = EventsFolder:WaitForChild("GameStarted")
local PlayerJoinedEvent = EventsFolder:WaitForChild("PlayerJoined")
local PlayerLeftEvent = EventsFolder:WaitForChild("PlayerLeft")

print("GameManager: Initializing...")

-- Load player data
local function loadPlayerData(player)
    local success, data = pcall(function()
        return PlayerDataStore:GetAsync("player_" .. player.UserId)
    end)
    
    if success and data then
        return data
    end
    
    -- Default data for new players
    return {
        Level = 1,
        Experience = 0,
        Currency = 0,
        Inventory = {},
        LastLogin = os.time()
    }
end

-- Save player data
local function savePlayerData(player, data)
    pcall(function()
        PlayerDataStore:SetAsync("player_" .. player.UserId, data)
    end)
end

-- Player join handler
Players.PlayerAdded:Connect(function(player)
    print("GameManager: Player joined - " .. player.Name)
    
    local playerData = loadPlayerData(player)
    
    -- Initialize player in game state
    GameState.ActivePlayers[player.UserId] = {
        Name = player.Name,
        Data = playerData,
        JoinedAt = os.time()
    }
    
    -- Fire event to other systems
    PlayerJoinedEvent:FireAllClients(player, playerData)
end)

-- Player leave handler
Players.PlayerRemoving:Connect(function(player)
    print("GameManager: Player left - " .. player.Name)
    
    local data = GameState.ActivePlayers[player.UserId]
    if data then
        savePlayerData(player, data.Data)
        GameState.ActivePlayers[player.UserId] = nil
    end
    
    PlayerLeftEvent:FireAllClients(player)
end)

-- Start game function
function GameState:start()
    self.IsRunning = true
    self.StartTime = os.time()
    
    print("GameManager: Game started!")
    GameStartedEvent:FireAllClients(true)
end

-- Stop game function
function GameState:stop()
    self.IsRunning = false
    self.EndTime = os.time()
    
    -- Save all player data
    for _, playerData in pairs(self.ActivePlayers) do
        local player = Players:FindFirstChild(playerData.Name)
        if player then
            savePlayerData(player, playerData.Data)
        end
    end
    
    print("GameManager: Game stopped!")
end

-- Get active players count
function GameState:getActivePlayerCount()
    return #self.ActivePlayers
end

-- Main loop
task.spawn(function()
    print("GameManager: Ready to start")
    
    -- Wait for initial setup
    wait(5)
    
    -- Auto-start after delay (can be triggered manually too)
    task.delay(10, function()
        GameState:start()
    end)
end)

return GameState
