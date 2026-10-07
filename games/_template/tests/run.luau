-- Minimal headless test runner (Lune). Exits non-zero on any failure.
local process = require("@lune/process")

local suites = {
	Economy = require("./unit/Economy.spec"),
}

local passed, failed = 0, 0
for suiteName, tests in suites do
	for name, fn in tests do
		local ok, err = pcall(fn)
		if ok then
			passed += 1
		else
			failed += 1
			print(string.format("FAIL %s > %s\n  %s", suiteName, name, tostring(err)))
		end
	end
end
print(string.format("%d passed, %d failed", passed, failed))
process.exit(if failed == 0 then 0 else 1)
