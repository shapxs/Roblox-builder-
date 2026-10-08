--!strict
-- Persistence abstraction. Uses DataStoreService in live servers and in-memory storage
-- in Studio or whenever DataStores are unavailable, so playtests never crash on saves.

local DataStoreService = game:GetService("DataStoreService")
local RunService = game:GetService("RunService")

local Economy = require(game:GetService("ReplicatedStorage").Shared.Economy)

local STORE_NAME = "PlayerData_v1"
local MAX_ATTEMPTS = 3

local PlayerData = {}

local store: DataStore? = nil
local memory: { [string]: any } = {}

-- Studio playtests never touch real player data: they use memory.
if not RunService:IsStudio() then
	local ok, result = pcall(function()
		return DataStoreService:GetDataStore(STORE_NAME)
	end)
	if ok then
		store = result
	else
		warn("[PlayerData] DataStore unavailable, using memory:", result)
	end
end

-- Studio without "Enable Studio Access to API Services" rejects every call; retrying
-- cannot help, so switch to memory for the rest of the session.
local function isPermanent(err: any): boolean
	return string.find(tostring(err), "not allowed", 1, true) ~= nil
end

local function withRetry<T>(label: string, fn: () -> T): (boolean, T?)
	for attempt = 1, MAX_ATTEMPTS do
		local ok, result = pcall(fn)
		if ok then
			return true, result
		end
		if isPermanent(result) then
			warn("[PlayerData] DataStore not allowed here, using memory")
			store = nil
			return false, nil
		end
		warn(
			string.format(
				"[PlayerData] %s failed (attempt %d): %s",
				label,
				attempt,
				tostring(result)
			)
		)
		task.wait(2 ^ attempt)
	end
	return false, nil
end

function PlayerData.load(userId: number): Economy.State
	local key = tostring(userId)
	local activeStore = store
	if activeStore == nil then
		return Economy.sanitize(memory[key])
	end
	local ok, raw = withRetry("load", function()
		return activeStore:GetAsync(key)
	end)
	if not ok then
		return Economy.sanitize(if store == nil then memory[key] else nil)
	end
	return Economy.sanitize(raw)
end

function PlayerData.save(userId: number, state: Economy.State): boolean
	local key = tostring(userId)
	local snapshot = { cash = state.cash, carried = state.carried, level = state.level }
	local activeStore = store
	if activeStore == nil then
		memory[key] = snapshot
		return true
	end
	local ok = withRetry("save", function()
		activeStore:SetAsync(key, snapshot)
		return true
	end)
	return ok
end

return PlayerData
