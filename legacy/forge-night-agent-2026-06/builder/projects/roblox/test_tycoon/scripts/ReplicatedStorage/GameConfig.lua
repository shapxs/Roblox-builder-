-- GameConfig.lua
-- Shared configuration constants

local GameConfig = {}

-- Game Information
GameConfig.GameName = "Test Tycoon"
GameConfig.GameId = 0  -- Replace with actual Roblox game ID
GameConfig.Version = "1.0.0"

-- Gameplay Settings
GameConfig.TargetAge = "8-14"
GameConfig.Genre = "tycoon"
GameConfig.Theme = "space"

-- Core Mechanics
GameConfig.CoreMechanic = "Build and manage a space mining operation"
GameConfig.Hook = "Real-time asteroid events"

-- Monetization
GameConfig.MonetizationStrategy = {
    VIPPassPrice = 499,
    PremiumResourcesPrice = 199,
    SkinPackAPrice = 299,
    XPBoostPrice = 99,
    CurrencyBundlePrice = 499
}

-- Progression Settings
GameConfig.LevelSystem = {
    MaxLevel = 100,
    XPPerLevelBase = 100,
    XPMultiplier = 1.5
}

-- Multiplayer Settings
GameConfig.MaxPlayers = 50
GameConfig.TeamSize = 4

-- Safety & Compliance
GameConfig.SafeChatEnabled = true
GameConfig.ParentalControls = true
GameConfig.ContentRating = "E10+"

return GameConfig
