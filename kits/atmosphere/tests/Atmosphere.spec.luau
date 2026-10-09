--!strict
-- Atmosphere kit: preset data and blending (Studio is not needed).

local Atmosphere = require("../../src/shared/Kits/Atmosphere")

local tests: { [string]: () -> () } = {}

local function eq(actual: any, expected: any, label: string)
	if actual ~= expected then
		error(
			string.format("%s: expected %s, got %s", label, tostring(expected), tostring(actual)),
			2
		)
	end
end

tests["every preset is complete and in range"] = function()
	local count = 0
	for name, preset in Atmosphere.Presets do
		local problem = Atmosphere.validate(preset)
		eq(problem, nil, name)
		count += 1
	end
	eq(count >= 6, true, "at least six presets")
end

tests["blend interpolates and clamps"] = function()
	local half = Atmosphere.blend("day", "night", 0.5)
	eq(half.clockTime, 7, "clockTime midpoint")
	eq(Atmosphere.validate(half), nil, "blend is valid")
	eq(
		Atmosphere.blend("day", "night", 5).brightness,
		Atmosphere.Presets.night.brightness,
		"clamped"
	)
	eq(Atmosphere.blend("day", "night", -1).density, Atmosphere.Presets.day.density, "clamped low")
end

tests["validate catches bad values"] = function()
	local bad = table.clone(Atmosphere.Presets.day) :: any
	bad.density = 2
	eq(Atmosphere.validate(bad), "density must be 0..1", "density")
	bad = table.clone(Atmosphere.Presets.day) :: any
	bad.tint = { 300, 0, 0 }
	eq(Atmosphere.validate(bad), "tint components must be integers 0..255", "tint")
end

return tests
