--!strict
-- Atmosphere kit: named lighting moods applied in one call.
-- Presets are plain data (RGB triples), so they can be unit-tested without Studio;
-- `apply` turns a preset into Lighting properties plus an Atmosphere instance.
--
--   local Atmosphere = require(ReplicatedStorage.Shared.Kits.Atmosphere)
--   Atmosphere.apply(game:GetService("Lighting"), "twilight")
--   Atmosphere.apply(Lighting, Atmosphere.blend("twilight", "sunset", 0.5))

export type RGB = { number }

export type Preset = {
	clockTime: number, -- 0..24
	brightness: number, -- Lighting.Brightness
	ambient: RGB, -- Lighting.Ambient
	outdoorAmbient: RGB, -- Lighting.OutdoorAmbient
	fogColor: RGB, -- Atmosphere.Color
	density: number, -- Atmosphere.Density 0..1 (volumetric fog thickness)
	haze: number, -- Atmosphere.Haze 0..10
	glare: number, -- Atmosphere.Glare 0..10
	decay: RGB, -- Atmosphere.Decay
	saturation: number, -- ColorCorrection.Saturation -1..1
	tint: RGB, -- ColorCorrection.TintColor
}

local Atmosphere = {}

Atmosphere.Presets = table.freeze({
	day = table.freeze({
		clockTime = 14,
		brightness = 2,
		ambient = { 120, 120, 120 },
		outdoorAmbient = { 140, 140, 140 },
		fogColor = { 199, 220, 255 },
		density = 0.25,
		haze = 1,
		glare = 0,
		decay = { 106, 112, 125 },
		saturation = 0,
		tint = { 255, 255, 255 },
	} :: Preset),
	sunset = table.freeze({
		clockTime = 18,
		brightness = 1.6,
		ambient = { 110, 80, 70 },
		outdoorAmbient = { 150, 110, 90 },
		fogColor = { 255, 170, 120 },
		density = 0.32,
		haze = 2,
		glare = 0.6,
		decay = { 170, 100, 80 },
		saturation = 0.1,
		tint = { 255, 236, 220 },
	} :: Preset),
	twilight = table.freeze({
		clockTime = 19.6,
		brightness = 0.8,
		ambient = { 40, 35, 70 },
		outdoorAmbient = { 70, 60, 110 },
		fogColor = { 70, 60, 120 },
		density = 0.42,
		haze = 2.5,
		glare = 0,
		decay = { 60, 50, 100 },
		saturation = 0.05,
		tint = { 220, 215, 255 },
	} :: Preset),
	night = table.freeze({
		clockTime = 0,
		brightness = 0.4,
		ambient = { 25, 25, 45 },
		outdoorAmbient = { 35, 35, 60 },
		fogColor = { 20, 20, 40 },
		density = 0.45,
		haze = 1.5,
		glare = 0,
		decay = { 15, 15, 30 },
		saturation = -0.05,
		tint = { 200, 205, 255 },
	} :: Preset),
	spooky = table.freeze({
		clockTime = 21,
		brightness = 0.6,
		ambient = { 35, 45, 40 },
		outdoorAmbient = { 50, 65, 55 },
		fogColor = { 60, 80, 70 },
		density = 0.55,
		haze = 3,
		glare = 0,
		decay = { 40, 55, 45 },
		saturation = -0.25,
		tint = { 210, 235, 220 },
	} :: Preset),
	underwater = table.freeze({
		clockTime = 12,
		brightness = 1.2,
		ambient = { 40, 90, 120 },
		outdoorAmbient = { 60, 120, 150 },
		fogColor = { 40, 120, 160 },
		density = 0.6,
		haze = 2,
		glare = 0,
		decay = { 30, 90, 130 },
		saturation = 0.15,
		tint = { 190, 230, 255 },
	} :: Preset),
})

local function clamp01(x: number): number
	return math.clamp(x, 0, 1)
end

-- Check a preset is complete and in range; returns the first problem or nil.
function Atmosphere.validate(preset: Preset): string?
	local function rgb(name: string, value: RGB): string?
		if #value ~= 3 then
			return name .. " must have 3 components"
		end
		for _, c in value do
			if c < 0 or c > 255 or c ~= math.floor(c) then
				return name .. " components must be integers 0..255"
			end
		end
		return nil
	end
	if preset.clockTime < 0 or preset.clockTime > 24 then
		return "clockTime must be 0..24"
	end
	if preset.brightness < 0 or preset.brightness > 10 then
		return "brightness must be 0..10"
	end
	if preset.density < 0 or preset.density > 1 then
		return "density must be 0..1"
	end
	if preset.haze < 0 or preset.haze > 10 or preset.glare < 0 or preset.glare > 10 then
		return "haze and glare must be 0..10"
	end
	if preset.saturation < -1 or preset.saturation > 1 then
		return "saturation must be -1..1"
	end
	for _, field in { "ambient", "outdoorAmbient", "fogColor", "decay", "tint" } do
		local problem = rgb(field, (preset :: any)[field])
		if problem then
			return problem
		end
	end
	return nil
end

-- Linear blend between two presets (t = 0 -> a, 1 -> b); handy for day/night cycles.
function Atmosphere.blend(a: string | Preset, b: string | Preset, t: number): Preset
	local pa = if type(a) == "string" then Atmosphere.Presets[a] else a
	local pb = if type(b) == "string" then Atmosphere.Presets[b] else b
	assert(pa and pb, "unknown preset")
	local k = clamp01(t)
	local function mix(x: number, y: number): number
		return x * (1 - k) + y * k -- exact at both ends
	end
	local function mixRGB(x: RGB, y: RGB): RGB
		return {
			math.round(mix(x[1], y[1])),
			math.round(mix(x[2], y[2])),
			math.round(mix(x[3], y[3])),
		}
	end
	return {
		clockTime = mix(pa.clockTime, pb.clockTime),
		brightness = mix(pa.brightness, pb.brightness),
		ambient = mixRGB(pa.ambient, pb.ambient),
		outdoorAmbient = mixRGB(pa.outdoorAmbient, pb.outdoorAmbient),
		fogColor = mixRGB(pa.fogColor, pb.fogColor),
		density = mix(pa.density, pb.density),
		haze = mix(pa.haze, pb.haze),
		glare = mix(pa.glare, pb.glare),
		decay = mixRGB(pa.decay, pb.decay),
		saturation = mix(pa.saturation, pb.saturation),
		tint = mixRGB(pa.tint, pb.tint),
	}
end

-- Apply a preset (by name or value) to Lighting. Creates or reuses one Atmosphere
-- and one ColorCorrectionEffect named "KitAtmosphere".
function Atmosphere.apply(lighting: Lighting, preset: string | Preset)
	local p = if type(preset) == "string" then Atmosphere.Presets[preset] else preset
	assert(p, "unknown atmosphere preset")
	local problem = Atmosphere.validate(p)
	assert(problem == nil, problem)
	local function color(c: RGB): Color3
		return Color3.fromRGB(c[1], c[2], c[3])
	end
	lighting.ClockTime = p.clockTime
	lighting.Brightness = p.brightness
	lighting.Ambient = color(p.ambient)
	lighting.OutdoorAmbient = color(p.outdoorAmbient)

	local atmosphere = lighting:FindFirstChild("KitAtmosphere") :: Atmosphere?
	if atmosphere == nil then
		local created = Instance.new("Atmosphere")
		created.Name = "KitAtmosphere"
		created.Parent = lighting
		atmosphere = created
	end
	assert(atmosphere, "Atmosphere missing")
	atmosphere.Color = color(p.fogColor)
	atmosphere.Decay = color(p.decay)
	atmosphere.Density = p.density
	atmosphere.Haze = p.haze
	atmosphere.Glare = p.glare

	local grade = lighting:FindFirstChild("KitGrade") :: ColorCorrectionEffect?
	if grade == nil then
		local created = Instance.new("ColorCorrectionEffect")
		created.Name = "KitGrade"
		created.Parent = lighting
		grade = created
	end
	assert(grade, "ColorCorrectionEffect missing")
	grade.Saturation = p.saturation
	grade.TintColor = color(p.tint)
end

return Atmosphere
