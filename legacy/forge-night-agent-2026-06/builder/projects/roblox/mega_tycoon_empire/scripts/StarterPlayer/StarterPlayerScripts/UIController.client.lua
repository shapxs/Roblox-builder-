-- UIController.client.lua
-- Main UI management and HUD

local Players = game:GetService("Players")
local UserInputService = game:GetService("UserInputService")
local ReplicatedStorage = game:GetService("ReplicatedStorage")

local Player = Players.LocalPlayer
local PlayerGui = Player:WaitForChild("PlayerGui")

-- Events
local EventsFolder = ReplicatedStorage:WaitForChild("Events")
local PurchaseCompletedEvent = EventsFolder:WaitForChild("PurchaseCompleted")

print("UIController: Initialized")

-- UI Screens
local Screens = {}

-- Create main menu screen
function createMainMenu()
    local screenGui = Instance.new("ScreenGui")
    screenGui.Name = "MainMenu"
    screenGui.ResetOnSpawn = false
    
    -- Main frame
    local mainFrame = Instance.new("Frame")
    mainFrame.Size = UDim2.new(0, 400, 0, 300)
    mainFrame.Position = UDim2.new(0.5, -200, 0.5, -150)
    mainFrame.AnchorPoint = Vector2.new(0.5, 0.5)
    mainFrame.BackgroundColor3 = Color3.fromRGB(40, 40, 60)
    mainFrame.Parent = screenGui
    
    -- Title label
    local title = Instance.new("TextLabel")
    title.Size = UDim2.new(1, -40, 0, 50)
    title.Position = UDim2.new(0, 20, 0, 10)
    title.Text = "GAME TITLE"
    title.Font = Enum.Font.GothamBold
    title.TextSize = 36
    title.TextColor3 = Color3.fromRGB(255, 255, 255)
    title.Parent = mainFrame
    
    -- Play button
    local playButton = Instance.new("TextButton")
    playButton.Size = UDim2.new(1, -40, 0, 40)
    playButton.Position = UDim2.new(0, 20, 0, 80)
    playButton.Text = "PLAY"
    playButton.Font = Enum.Font.GothamBold
    playButton.BackgroundColor3 = Color3.fromRGB(76, 187, 239)
    playButton.Parent = mainFrame
    
    -- Shop button
    local shopButton = Instance.new("TextButton")
    shopButton.Size = UDim2.new(1, -40, 0, 40)
    shopButton.Position = UDim2.new(0, 20, 0, 130)
    shopButton.Text = "SHOP"
    shopButton.Font = Enum.Font.GothamBold
    shopButton.BackgroundColor3 = Color3.fromRGB(76, 187, 239)
    shopButton.Parent = mainFrame
    
    -- Settings button
    local settingsButton = Instance.new("TextButton")
    settingsButton.Size = UDim2.new(1, -40, 0, 40)
    settingsButton.Position = UDim2.new(0, 20, 0, 180)
    settingsButton.Text = "SETTINGS"
    settingsButton.Font = Enum.Font.GothamBold
    settingsButton.BackgroundColor3 = Color3.fromRGB(76, 187, 239)
    settingsButton.Parent = mainFrame
    
    return screenGui
end

-- Create HUD
function createHUD()
    local screenGui = Instance.new("ScreenGui")
    screenGui.Name = "HUD"
    screenGui.ResetOnSpawn = false
    
    -- Currency display
    local currencyFrame = Instance.new("Frame")
    currencyFrame.Size = UDim2.new(0, 200, 0, 50)
    currencyFrame.Position = UDim2.new(0.5, -100, 0, 10)
    currencyFrame.BackgroundColor3 = Color3.fromRGB(40, 40, 60)
    currencyFrame.Parent = screenGui
    
    local currencyLabel = Instance.new("TextLabel")
    currencyLabel.Size = UDim2.new(1, 0, 1, 0)
    currencyLabel.Text = "Robux: 0"
    currencyLabel.Font = Enum.Font.GothamBold
    currencyLabel.TextSize = 24
    currencyLabel.TextColor3 = Color3.fromRGB(76, 187, 239)
    currencyLabel.Parent = currencyFrame
    
    -- Level display
    local levelFrame = Instance.new("Frame")
    levelFrame.Size = UDim2.new(0, 150, 0, 40)
    levelFrame.Position = UDim2.new(0.5, -75, 0, 70)
    levelFrame.BackgroundColor3 = Color3.fromRGB(40, 40, 60)
    levelFrame.Parent = screenGui
    
    local levelLabel = Instance.new("TextLabel")
    levelLabel.Size = UDim2.new(1, 0, 1, 0)
    levelLabel.Text = "Level: 1"
    levelLabel.Font = Enum.Font.GothamBold
    levelLabel.TextSize = 20
    levelLabel.TextColor3 = Color3.fromRGB(255, 255, 255)
    levelLabel.Parent = levelFrame
    
    return screenGui
end

-- Event handlers
PurchaseCompletedEvent.OnClientEvent:Connect(function(productName)
    print("UIController: Purchase completed - " .. productName)
    
    -- Show confirmation
    local confirmation = Instance.new("TextLabel")
    confirmation.Size = UDim2.new(0, 300, 0, 50)
    confirmation.Position = UDim2.new(0.5, -150, 0.5, -25)
    confirmation.Text = "Purchase Successful!"
    confirmation.BackgroundTransparency = 1
    confirmation.TextColor3 = Color3.fromRGB(76, 187, 239)
    confirmation.Font = Enum.Font.GothamBold
    confirmation.TextSize = 30
    confirmation.Parent = PlayerGui
    
    task.delay(3, function()
        if confirmation and confirmation.Parent then
            confirmation:Destroy()
        end
    end)
end)

-- Initialize UI on player join
Player.CharacterAdded:Connect(function(character)
    wait(1) -- Wait for character to load
    
    -- Show HUD
    local hud = PlayerGui:FindFirstChild("HUD")
    if not hud then
        hud = createHUD()
        hud.Parent = PlayerGui
    end
end)

-- Main initialization
task.spawn(function()
    print("UIController: Setting up UI...")
    
    -- Create main menu (shown initially)
    local mainMenu = createMainMenu()
    mainMenu.Parent = PlayerGui
    
    print("UIController: Ready")
end)

return {
    CreateHUD = createHUD,
    CreateMainMenu = createMainMenu
}
