--!strict
-- Feedback kit: make every action feel rewarding. Client-side effects (floating
-- "+5" pop-ups, HUD bounce, coloured flash) and a server-side particle burst, plus
-- pure helpers for formatting and pop-up placement that are unit-tested.
--
-- Client:
--   local Feedback = require(ReplicatedStorage.Shared.Kits.Feedback)
--   Feedback.popup(hudLabel.Parent, Feedback.delta(5), Feedback.color("reward"))
--   Feedback.bounce(hudLabel)
-- Server:
--   Feedback.burst(collectPart, Feedback.color("reward"))
--
-- Roblox services and Color3 are only touched inside functions, so the pure helpers
-- can be unit-tested headless.

local Feedback = {}

-- Named colours as RGB data.
Feedback.Palette = table.freeze({
	reward = { 255, 214, 90 },
	gain = { 120, 230, 140 },
	loss = { 240, 110, 110 },
	info = { 150, 200, 255 },
	magic = { 190, 140, 255 },
})

function Feedback.color(name: string): Color3
	local rgb = Feedback.Palette[name]
	assert(rgb, "unknown feedback colour " .. name)
	return Color3.fromRGB(rgb[1], rgb[2], rgb[3])
end

local function tweens(): TweenService
	return game:GetService("TweenService")
end

-- "+5", "-12", "+1,250" (thousands separators). Pure.
function Feedback.delta(amount: number): string
	local n = math.floor(math.abs(amount))
	local digits = tostring(n)
	local grouped = digits:reverse():gsub("(%d%d%d)", "%1,"):reverse()
	if grouped:sub(1, 1) == "," then
		grouped = grouped:sub(2)
	end
	return (if amount < 0 then "-" else "+") .. grouped
end

-- Horizontal offset (scale, -0.5..0.5) for the i-th simultaneous pop-up so stacked
-- pop-ups fan out instead of overlapping. Pure.
function Feedback.spread(index: number, count: number): number
	if count <= 1 then
		return 0
	end
	local step = math.min(0.12, 0.8 / (count - 1))
	return (index - 1) * step - step * (count - 1) / 2
end

-- Floating text that rises and fades over ~0.9 s inside `parent` (a ScreenGui or frame).
function Feedback.popup(parent: Instance, text: string, color: Color3?, offset: number?)
	local label = Instance.new("TextLabel")
	label.Name = "KitPopup"
	label.BackgroundTransparency = 1
	label.AnchorPoint = Vector2.new(0.5, 0.5)
	label.Position = UDim2.fromScale(0.5 + (offset or 0), 0.42)
	label.Size = UDim2.fromOffset(160, 40)
	label.Font = Enum.Font.GothamBlack
	label.TextScaled = true
	label.Text = text
	label.TextColor3 = color or Feedback.color("reward")
	label.TextStrokeTransparency = 0.4
	label.Parent = parent
	local info = TweenInfo.new(0.9, Enum.EasingStyle.Quad, Enum.EasingDirection.Out)
	tweens()
		:Create(label, info, {
			Position = label.Position - UDim2.fromScale(0, 0.12),
			TextTransparency = 1,
			TextStrokeTransparency = 1,
		})
		:Play()
	task.delay(1, function()
		label:Destroy()
	end)
end

-- Quick scale "bounce" on a GUI object (adds a UIScale if it has none).
function Feedback.bounce(target: GuiObject)
	local scale = target:FindFirstChildOfClass("UIScale")
	if scale == nil then
		local created = Instance.new("UIScale")
		created.Parent = target
		scale = created
	end
	assert(scale, "UIScale missing")
	scale.Scale = 1.15
	tweens():Create(scale, TweenInfo.new(0.25, Enum.EasingStyle.Back), { Scale = 1 }):Play()
end

-- Brief colour flash on a GUI object's background.
function Feedback.flash(target: GuiObject, color: Color3)
	local original = target.BackgroundColor3
	target.BackgroundColor3 = color
	tweens():Create(target, TweenInfo.new(0.35), { BackgroundColor3 = original }):Play()
end

-- Server or client: a short particle burst at a part (e.g. a collected item).
function Feedback.burst(part: BasePart, color: Color3, amount: number?)
	local attachment = Instance.new("Attachment")
	attachment.Parent = part
	local emitter = Instance.new("ParticleEmitter")
	emitter.Color = ColorSequence.new(color)
	emitter.LightEmission = 0.8
	emitter.Size = NumberSequence.new({
		NumberSequenceKeypoint.new(0, 0.4),
		NumberSequenceKeypoint.new(1, 0),
	})
	emitter.Lifetime = NumberRange.new(0.4, 0.8)
	emitter.Speed = NumberRange.new(6, 12)
	emitter.SpreadAngle = Vector2.new(180, 180)
	emitter.Enabled = false
	emitter.Parent = attachment
	emitter:Emit(amount or 20)
	task.delay(1.2, function()
		attachment:Destroy()
	end)
end

return Feedback
