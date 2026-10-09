--!strict
-- Feedback kit: formatting and pop-up placement (Studio is not needed).

local Feedback = require("../../src/shared/Kits/Feedback")

local tests: { [string]: () -> () } = {}

local function eq(actual: any, expected: any, label: string)
	if actual ~= expected then
		error(
			string.format("%s: expected %s, got %s", label, tostring(expected), tostring(actual)),
			2
		)
	end
end

tests["delta formats signed amounts with separators"] = function()
	eq(Feedback.delta(5), "+5", "small")
	eq(Feedback.delta(-12), "-12", "negative")
	eq(Feedback.delta(1250), "+1,250", "thousands")
	eq(Feedback.delta(1234567), "+1,234,567", "millions")
	eq(Feedback.delta(100), "+100", "no leading comma")
	eq(Feedback.delta(0), "+0", "zero")
end

tests["spread fans pop-ups symmetrically"] = function()
	eq(Feedback.spread(1, 1), 0, "single is centred")
	eq(Feedback.spread(1, 3) + Feedback.spread(3, 3), 0, "symmetric")
	eq(Feedback.spread(2, 3), 0, "middle is centred")
	eq(math.abs(Feedback.spread(1, 20)) <= 0.5, true, "stays on screen")
end

tests["palette entries are valid RGB"] = function()
	for name, rgb in Feedback.Palette do
		eq(#rgb, 3, name)
		for _, c in rgb do
			eq(c >= 0 and c <= 255, true, name)
		end
	end
end

return tests
