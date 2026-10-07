-- DataStore.server.lua
-- Player data persistence and management

local DataStoreService = game:GetService("DataStoreService")
local Players = game:GetService("Players")

-- Data stores
local PlayerDataStore = DataStoreService:GetDataStore("PlayerData")
local GlobalDataStore = DataStoreService:GetDataStore("GlobalData")

print("DataStore: Initialized")

-- Get player data
function getPlayerData(player)
    local success, data = pcall(function()
        return PlayerDataStore:GetAsync("player_" .. player.UserId)
    end)
    
    if success and data then
        return data
    end
    
    -- Return default data for new players
    return {
        Level = 1,
        Experience = 0,
        Currency = 0,
        Inventory = {},
        LastLogin = os.time(),
        TotalPlayTime = 0
    }
end

-- Update player data
function updatePlayerData(player, newData)
    pcall(function()
        PlayerDataStore:SetAsync("player_" .. player.UserId, newData)
    end)
end

-- Increment global counter
function incrementGlobalCounter(counterName)
    local success, result = pcall(function()
        return GlobalDataStore:IncrementAsync(counterName, 1)
    end)
    
    if success then
        return result
    end
    
    return nil
end

-- Get global data
function getGlobalData(key)
    local success, data = pcall(function()
        return GlobalDataStore:GetAsync(key)
    end)
    
    if success and data then
        return data
    end
    
    return nil
end

-- Player leave handler - save data
Players.PlayerRemoving:Connect(function(player)
    print("DataStore: Saving data for " .. player.Name)
    
    local success = pcall(function()
        -- This would be called from GameManager
        -- Data is saved in the main game loop
    end)
end)

return {
    GetPlayerData = getPlayerData,
    UpdatePlayerData = updatePlayerData,
    IncrementGlobalCounter = incrementGlobalCounter,
    GetGlobalData = getGlobalData
}
