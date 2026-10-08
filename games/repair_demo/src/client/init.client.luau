--!strict
-- HUD: renders the server-owned player attributes. Sends nothing to the server.

local Players = game:GetService("Players")

local player = Players.LocalPlayer

local gui = Instance.new("ScreenGui")
gui.Name = "MainHUD"
gui.ResetOnSpawn = false
gui.Parent = player:WaitForChild("PlayerGui")

local label = Instance.new("TextLabel")
label.Name = "Stats"
label.AnchorPoint = Vector2.new(0.5, 0)
label.Position = UDim2.new(0.5, 0, 0, 12)
label.Size = UDim2.fromOffset(360, 44)
label.BackgroundColor3 = Color3.fromRGB(20, 20, 28)
label.BackgroundTransparency = 0.25
label.TextColor3 = Color3.new(1, 1, 1)
label.Font = Enum.Font.GothamBold
label.TextScaled = true
label.Parent = gui

local corner = Instance.new("UICorner")
corner.CornerRadius = UDim.new(0, 8)
corner.Parent = label

local function render()
	local cash = player:GetAttribute("Cash") or 0
	local carried = player:GetAttribute("Carried") or 0
	local capacity = player:GetAttribute("Capacity") or 0
	local cost = player:GetAttribute("UpgradeCost") or 0
	label.Text = string.format("Cash: %d   Bag: %d/%d   Upgrade: %d", cash, carried, capacity, cost)
end

for _, name in { "Cash", "Carried", "Capacity", "UpgradeCost" } do
	player:GetAttributeChangedSignal(name):Connect(render)
end
render()
