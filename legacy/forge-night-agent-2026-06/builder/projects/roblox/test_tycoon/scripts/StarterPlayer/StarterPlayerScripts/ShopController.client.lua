-- ShopController.client.lua
-- In-game shop interface and functionality

local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")

local Player = Players.LocalPlayer
local PlayerGui = Player:WaitForChild("PlayerGui")

-- Events
local EventsFolder = ReplicatedStorage:WaitForChild("Events")
local PurchaseCompletedEvent = EventsFolder:WaitForChild("PurchaseCompleted")

print("ShopController: Initialized")

-- Shop items (from GameConfig)
local SHOP_ITEMS = {
    GamePasses = {
        { Id = 0, Name = "VIP Pass", Price = 499, Description = "Exclusive VIP benefits" },
        { Id = 0, Name = "Premium Resources", Price = 199, Description = "Starter resource bundle" }
    },
    Products = {
        { Id = 0, Name = "Skin Pack A", Price = 299, Description = "Cool character skins" },
        { Id = 0, Name = "XP Boost (24h)", Price = 99, Description = "Double XP for 24 hours" },
        { Id = 0, Name = "Currency Bundle", Price = 499, Description = "Extra currency" }
    }
}

-- Shop GUI
local ShopGui = nil

-- Open shop function
function openShop()
    if ShopGui then
        ShopGui:Destroy()
    end
    
    ShopGui = Instance.new("ScreenGui")
    ShopGui.Name = "Shop"
    ShopGui.ResetOnSpawn = false
    
    -- Main frame
    local mainFrame = Instance.new("Frame")
    mainFrame.Size = UDim2.new(0, 600, 0, 500)
    mainFrame.Position = UDim2.new(0.5, -300, 0.5, -250)
    mainFrame.AnchorPoint = Vector2.new(0.5, 0.5)
    mainFrame.BackgroundColor3 = Color3.fromRGB(40, 40, 60)
    mainFrame.Parent = ShopGui
    
    -- Title
    local title = Instance.new("TextLabel")
    title.Size = UDim2.new(1, -40, 0, 50)
    title.Position = UDim2.new(0, 20, 0, 10)
    title.Text = "ITEM SHOP"
    title.Font = Enum.Font.GothamBold
    title.TextSize = 36
    title.TextColor3 = Color3.fromRGB(255, 255, 255)
    title.Parent = mainFrame
    
    -- Close button
    local closeBtn = Instance.new("TextButton")
    closeBtn.Size = UDim2.new(0, 100, 0, 40)
    closeBtn.Position = UDim2.new(1, -120, 0, 10)
    closeBtn.Text = "CLOSE"
    closeBtn.Font = Enum.Font.GothamBold
    closeBtn.BackgroundColor3 = Color3.fromRGB(239, 76, 76)
    closeBtn.Parent = mainFrame
    
    -- Items container
    local itemsContainer = Instance.new("ScrollingFrame")
    itemsContainer.Size = UDim2.new(1, -40, 0, 350)
    itemsContainer.Position = UDim2.new(0, 20, 0, 70)
    itemsContainer.CanvasSize = UDim2.new(0, 0, 0, 0)
    itemsContainer.BackgroundColor3 = Color3.fromRGB(60, 60, 80)
    itemsContainer.Parent = mainFrame
    
    -- Generate item buttons
    local yPosition = 10
    for _, item in ipairs(SHOP_ITEMS.GamePasses) do
        createItemButton(item, "Game Pass", yPosition, itemsContainer)
        yPosition = yPosition + 80
    end
    
    for _, item in ipairs(SHOP_ITEMS.Products) do
        createItemButton(item, "Product", yPosition, itemsContainer)
        yPosition = yPosition + 80
    end
    
    -- Currency display at bottom
    local currencyDisplay = Instance.new("TextLabel")
    currencyDisplay.Size = UDim2.new(1, -40, 0, 30)
    currencyDisplay.Position = UDim2.new(0, 20, 1, -40)
    currencyDisplay.Text = "Your Robux: 0"
    currencyDisplay.Font = Enum.Font.GothamBold
    currencyDisplay.TextSize = 20
    currencyDisplay.TextColor3 = Color3.fromRGB(76, 187, 239)
    currencyDisplay.Parent = mainFrame
    
    ShopGui.Parent = PlayerGui
end

-- Create item button
function createItemButton(item, itemType, yPosition, container)
    local itemFrame = Instance.new("Frame")
    itemFrame.Size = UDim2.new(1, -40, 0, 70)
    itemFrame.Position = UDim2.new(0, 20, 0, yPosition)
    itemFrame.BackgroundColor3 = Color3.fromRGB(50, 50, 70)
    itemFrame.Parent = container
    
    -- Item name
    local nameLabel = Instance.new("TextLabel")
    nameLabel.Size = UDim2.new(1, -160, 0, 30)
    nameLabel.Position = UDim2.new(0, 10, 0, 5)
    nameLabel.Text = item.Name
    nameLabel.Font = Enum.Font.GothamBold
    nameLabel.TextSize = 24
    nameLabel.TextColor3 = Color3.fromRGB(255, 255, 255)
    nameLabel.Parent = itemFrame
    
    -- Item description
    local descLabel = Instance.new("TextLabel")
    descLabel.Size = UDim2.new(1, -160, 0, 20)
    descLabel.Position = UDim2.new(0, 10, 0, 35)
    descLabel.Text = item.Description
    descLabel.Font = Enum.Font.Gotham
    descLabel.TextSize = 16
    descLabel.TextColor3 = Color3.fromRGB(200, 200, 200)
    descLabel.Parent = itemFrame
    
    -- Price label
    local priceLabel = Instance.new("TextLabel")
    priceLabel.Size = UDim2.new(0, 100, 0, 30)
    priceLabel.Position = UDim2.new(1, -110, 0, 5)
    priceLabel.Text = item.Price .. " Robux"
    priceLabel.Font = Enum.Font.GothamBold
    priceLabel.TextSize = 24
    priceLabel.TextColor3 = Color3.fromRGB(76, 187, 239)
    priceLabel.Parent = itemFrame
    
    -- Buy button
    local buyBtn = Instance.new("TextButton")
    buyBtn.Size = UDim2.new(0, 80, 0, 30)
    buyBtn.Position = UDim2.new(1, -95, 0, 35)
    buyBtn.Text = "BUY"
    buyBtn.Font = Enum.Font.GothamBold
    buyBtn.BackgroundColor3 = Color3.fromRGB(76, 187, 239)
    buyBtn.Parent = itemFrame
    
    -- Buy handler
    buyBtn.MouseButton1Click:Connect(function()
        print("ShopController: Attempting purchase - " .. item.Name)
        
        -- In a real implementation, this would call the server
        -- For now, just show confirmation
        local confirmation = Instance.new("TextLabel")
        confirmation.Size = UDim2.new(0, 300, 0, 50)
        confirmation.Position = UDim2.new(0.5, -150, 0.5, -25)
        confirmation.Text = "Purchase Requested!"
        confirmation.BackgroundTransparency = 1
        confirmation.TextColor3 = Color3.fromRGB(76, 187, 239)
        confirmation.Font = Enum.Font.GothamBold
        confirmation.TextSize = 30
        confirmation.Parent = PlayerGui
        
        task.delay(2, function()
            if confirmation and confirmation.Parent then
                confirmation:Destroy()
            end
        end)
    end)
end

-- Event handlers
PurchaseCompletedEvent.OnClientEvent:Connect(function(productName)
    print("ShopController: Purchase completed - " .. productName)
    
    -- Update UI to show new items/unlocks
    if ShopGui then
        -- Refresh shop UI or show unlock notification
    end
end)

return {
    OpenShop = openShop,
    CreateItemButton = createItemButton
}
