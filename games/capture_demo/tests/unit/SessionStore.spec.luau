--!strict
-- Fault-injected persistence tests: failed loads, racing servers, stale locks.

local SessionStore = require("../../src/server/SessionStore")

local tests: { [string]: () -> () } = {}

local function eq(actual: any, expected: any, label: string)
	if actual ~= expected then
		error(
			string.format("%s: expected %s, got %s", label, tostring(expected), tostring(actual)),
			2
		)
	end
end

local now = 1000
local function clock(): number
	return now
end

-- A store whose UpdateAsync throws while `failing` is true (outage, throttling).
local function flakyStore()
	local store = SessionStore.MemoryStore.new()
	local flaky = { failing = false, rows = store.rows }
	function flaky.UpdateAsync(self: any, key: string, transform: (any) -> any): any
		if self.failing then
			error("502: DataStore request failed")
		end
		return store:UpdateAsync(key, transform)
	end
	return flaky
end

tests["a new player loads as new and the first save persists"] = function()
	local store = SessionStore.MemoryStore.new()
	local s = SessionStore.new(store, "server-A", clock)
	local result = s:load("p1")
	eq(result, "new", "load")
	eq(s:save("p1", { cash = 5 }, true), "saved", "save")
	local again = SessionStore.new(store, "server-B", clock)
	local r2, data = again:load("p1")
	eq(r2, "loaded", "reload")
	eq(data.cash, 5, "cash persisted")
end

tests["a failed load is never treated as a new player"] = function()
	local store = flakyStore()
	SessionStore.new(store, "old", clock):save("p1", {}, true) -- no session: lost_session
	store.rows["p1"] = { data = { cash = 999 }, version = 3 }
	store.failing = true
	local s = SessionStore.new(store, "server-A", clock)
	local result, data = s:load("p1")
	eq(result, "failed", "load during outage")
	eq(data, nil, "no data")
	store.failing = false
	-- Without a session this server cannot save, so 999 can never be overwritten.
	eq(s:save("p1", { cash = 0 }, true), "lost_session", "save refused")
	eq(store.rows["p1"].data.cash, 999, "real progress kept")
end

tests["a profile held by another live server is not taken"] = function()
	local store = SessionStore.MemoryStore.new()
	local a = SessionStore.new(store, "server-A", clock)
	local b = SessionStore.new(store, "server-B", clock)
	eq((a:load("p1")), "new", "A loads")
	eq((b:load("p1")), "locked", "B is locked out")
	eq(a:save("p1", { cash = 10 }, false), "saved", "A keeps saving")
	eq(b:save("p1", { cash = 0 }, true), "lost_session", "B cannot overwrite")
	eq(store.rows["p1"].data.cash, 10, "A's progress kept")
end

tests["releasing the session lets the next server load immediately"] = function()
	local store = SessionStore.MemoryStore.new()
	local a = SessionStore.new(store, "server-A", clock)
	a:load("p1")
	eq(a:save("p1", { cash = 7 }, true), "saved", "release")
	local b = SessionStore.new(store, "server-B", clock)
	local result, data = b:load("p1")
	eq(result, "loaded", "B loads")
	eq(data.cash, 7, "B sees A's save")
	eq(a:save("p1", { cash = 0 }, false), "lost_session", "A can no longer write")
end

tests["a stale lock from a crashed server is taken over"] = function()
	local store = SessionStore.MemoryStore.new()
	SessionStore.new(store, "crashed", clock):load("p1")
	now += 601
	eq((SessionStore.new(store, "server-B", clock):load("p1")), "new", "stale lock taken")
	now -= 601
end

tests["a corrupt record is reported and never overwritten"] = function()
	local store = SessionStore.MemoryStore.new()
	store.rows["p1"] = "garbage"
	local s = SessionStore.new(store, "server-A", clock)
	eq((s:load("p1")), "corrupt", "corrupt")
	eq(s:save("p1", { cash = 0 }, true), "lost_session", "no save")
	eq(store.rows["p1"], "garbage", "untouched")
end

tests["versions increase with every save"] = function()
	local store = SessionStore.MemoryStore.new()
	local s = SessionStore.new(store, "server-A", clock)
	s:load("p1")
	s:save("p1", { cash = 1 }, false)
	s:save("p1", { cash = 2 }, false)
	eq(store.rows["p1"].version, 2, "version")
end

tests["an older in-flight save cannot replace a newer snapshot"] = function()
	local store = SessionStore.MemoryStore.new()
	local s = SessionStore.new(store, "server-A", clock)
	s:load("p1")
	local original = store.UpdateAsync
	local race = true
	function store.UpdateAsync(self: any, key: string, transform: (any) -> any): any
		if race then
			race = false
			eq(s:save("p1", { cash = 20 }, false), "saved", "newer save")
		end
		return original(self, key, transform)
	end
	eq(s:save("p1", { cash = 10 }, false), "superseded", "older save refused")
	eq(store.rows["p1"].data.cash, 20, "newer cash kept")
end

tests["a save from an earlier load cannot write into a later lease"] = function()
	local store = SessionStore.MemoryStore.new()
	local s = SessionStore.new(store, "server-A", clock)
	s:load("p1")
	local oldToken = s:beginSave("p1")
	eq(s:save("p1", { cash = 10 }, true, oldToken), "saved", "old lease released")
	s:load("p1")
	eq(s:save("p1", { cash = 0 }, false, oldToken), "lost_session", "old lease refused")
	eq(store.rows["p1"].data.cash, 10, "progress kept")
end

tests["a same-server rejoin waits for the departing save"] = function()
	local store = SessionStore.MemoryStore.new()
	local s = SessionStore.new(store, "server-A", clock)
	s:load("p1")
	s:save("p1", { cash = 90 }, false)
	local pendingRelease = s:beginSave("p1")
	eq((s:load("p1")), "locked", "rejoin waits for release")
	eq(s:save("p1", { cash = 100 }, true, pendingRelease), "saved", "departure saved")
	local status, data = s:load("p1")
	eq(status, "loaded", "rejoin loaded")
	eq(data.cash, 100, "latest progress loaded")
end

return tests
