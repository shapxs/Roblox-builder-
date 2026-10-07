-- PlayerLib.lua
-- Shared player utility functions

local Players = game:GetService("Players")

local PlayerLib = {}

-- Get player by name (case-insensitive)
function PlayerLib.getPlayerByName(name)
    for _, player in ipairs(Players:GetPlayers()) do
        if string.lower(player.Name) == string.lower(name) then
            return player
        end
    end
    return nil
end

-- Get all players in a team
function PlayerLib.getTeamPlayers(teamName)
    local teamPlayers = {}
    
    for _, player in ipairs(Players:GetPlayers()) do
        if player.Team and player.Team.Name == teamName then
            table.insert(teamPlayers, player)
        end
    end
    
    return teamPlayers
end

-- Check if player is VIP
function PlayerLib.isVIP(player)
    -- This would check game pass ownership
    return false
end

-- Format number with commas
function PlayerLib.formatNumber(number)
    local formatted = tostring(math.floor(number))
    local k
    while true do
        formatted, k = string.gsub(formatted, "^(-?%d+)(%d%d%d)", '%1,%2')
        if k == 0 then
            break
        end
    end
    return formatted
end

-- Calculate XP needed for next level
function PlayerLib.getXPForNextLevel(level)
    return math.floor(100 * (1.5 ^ (level - 1)))
end

return PlayerLib
