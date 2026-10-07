-- MonetizationHandler.server.lua
-- Handles game passes and microtransactions

local MarketplaceService = game:GetService("MarketplaceService")
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")

-- Game IDs for passes (replace with actual Roblox game pass IDs)
local GAME_PASS_IDS = {
    VIPPass = 0,  -- Replace with actual ID
    PremiumResources = 0  -- Replace with actual ID
}

-- Product IDs for microtransactions (replace with actual IDs)
local PRODUCT_IDS = {
    SkinPackA = 0,
    SkinPackB = 0,
    XPBoost = 0,
    CurrencyBundle = 0
}

print("MonetizationHandler: Initialized")

-- Events
local EventsFolder = ReplicatedStorage:WaitForChild("Events")
local PurchaseCompletedEvent = EventsFolder:WaitForChild("PurchaseCompleted")

-- Check if player owns a game pass
function checkGamePassOwnership(player, gamePassId)
    local success, owned = pcall(function()
        return MarketplaceService:UserOwnsGamePassAsync(player.UserId, gamePassId)
    end)
    
    return success and owned or false
end

-- Process purchase
MarketplaceService.PromptProductPurchaseFinished:Connect(function(player, productId, purchased)
    if not purchased then
        return
    end
    
    print("MonetizationHandler: Purchase completed - " .. player.Name .. " - Product: " .. tostring(productId))
    
    -- Grant benefits based on product ID
    if productId == GAME_PASS_IDS.VIPPass then
        -- Grant VIP benefits
        PurchaseCompletedEvent:FireClient(player, "VIPPass")
    elseif productId == GAME_PASS_IDS.PremiumResources then
        -- Grant resource pack benefits
        PurchaseCompletedEvent:FireClient(player, "PremiumResources")
    elseif productId == PRODUCT_IDS.XPBoost then
        -- Grant XP boost
        PurchaseCompletedEvent:FireClient(player, "XPBoost")
    end
end)

-- Process game pass purchase
MarketplaceService.PromptGamePassPurchaseFinished:Connect(function(player, gamePassId, purchased)
    if not purchased then
        return
    end
    
    print("MonetizationHandler: Game Pass purchased - " .. player.Name)
    
    -- Grant game pass benefits
    PurchaseCompletedEvent:FireClient(player, "GamePass")
end)

-- Get VIP status
function isVIPPlayer(player)
    return checkGamePassOwnership(player, GAME_PASS_IDS.VIPPass)
end

-- Get all available products
function getAvailableProducts()
    return {
        GamePasses = {
            { Id = GAME_PASS_IDS.VIPPass, Name = "VIP Pass", Price = 499 },
            { Id = GAME_PASS_IDS.PremiumResources, Name = "Premium Resources", Price = 199 }
        },
        Products = {
            { Id = PRODUCT_IDS.SkinPackA, Name = "Skin Pack A", Price = 299 },
            { Id = PRODUCT_IDS.XPBoost, Name = "XP Boost (24h)", Price = 99 },
            { Id = PRODUCT_IDS.CurrencyBundle, Name = "Currency Bundle", Price = 499 }
        }
    }
end

return {
    CheckGamePassOwnership = checkGamePassOwnership,
    IsVIPPlayer = isVIPPlayer,
    GetAvailableProducts = getAvailableProducts
}
