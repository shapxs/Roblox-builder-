-- GameConfig.lua
-- Shared configuration constants

local GameConfig = {{}}

-- Game Information
GameConfig.GameName = "{concept.name}"
GameConfig.GameId = 0  -- Replace with actual Roblox game ID
GameConfig.Version = "1.0.0"

-- Gameplay Settings
GameConfig.TargetAge = "{concept.target_age}"
GameConfig.Genre = "{concept.genre}"
GameConfig.Theme = "{concept.theme}"

-- Core Mechanics
GameConfig.CoreMechanic = "{concept.core_mechanic}"
GameConfig.Hook = "{concept.hook}"

-- Monetization
GameConfig.MonetizationStrategy = {{
    VIPPassPrice = 499,
    PremiumResourcesPrice = 199,
    SkinPackAPrice = 299,
    XPBoostPrice = 99,
    CurrencyBundlePrice = 499
}}

-- Progression Settings
GameConfig.LevelSystem = {{
    MaxLevel = 100,
    XPPerLevelBase = 100,
    XPMultiplier = 1.5
}}

-- Multiplayer Settings
GameConfig.MaxPlayers = 50
GameConfig.TeamSize = 4

-- Safety & Compliance
GameConfig.SafeChatEnabled = true
GameConfig.ParentalControls = true
GameConfig.ContentRating = "E10+"

return GameConfig
