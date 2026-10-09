-- Minimal headless test runner (Lune). Runs every tests/unit/*.spec.luau, including the
-- specs installed with system kits, and exits non-zero on any failure or if no specs ran.
local fs = require("@lune/fs")
local process = require("@lune/process")

local UNIT = "tests/unit" -- relative to the game root, where `lune run tests/run.luau` runs

local names = {}
for _, name in fs.readDir(UNIT) do
	if name:match("%.spec%.luau$") then
		table.insert(names, name)
	end
end
table.sort(names)

local passed, failed = 0, 0
for _, file in names do
	local suiteName = file:gsub("%.spec%.luau$", "")
	local ok, tests = pcall(require, "./unit/" .. file:gsub("%.luau$", ""))
	if not ok then
		failed += 1
		print(string.format("FAIL %s (could not load)\n  %s", suiteName, tostring(tests)))
		continue
	end
	for name, fn in tests do
		local good, err = pcall(fn)
		if good then
			passed += 1
		else
			failed += 1
			print(string.format("FAIL %s > %s\n  %s", suiteName, name, tostring(err)))
		end
	end
end
print(string.format("%d passed, %d failed (%d suites)", passed, failed, #names))
process.exit(if failed == 0 and passed > 0 then 0 else 1)
