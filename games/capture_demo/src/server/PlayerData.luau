--!strict
-- Player progress persistence on top of SessionStore.
--
-- Live servers use DataStoreService; Studio playtests use an in-memory store with the
-- same session rules, so playtests exercise the same code path without touching real
-- player data. A player whose profile cannot be loaded safely is asked to rejoin
-- rather than playing on defaults that could later overwrite real progress.

local DataStoreService = game:GetService("DataStoreService")
local HttpService = game:GetService("HttpService")
local RunService = game:GetService("RunService")

local Economy = require(game:GetService("ReplicatedStorage").Shared.Economy)
local SessionStore = require(script.Parent.SessionStore)

local STORE_NAME = "PlayerData_v2"
local LOAD_ATTEMPTS = 4
local LOCKED_RETRY_SECONDS = 3
local SAVE_ATTEMPTS = 3

local PlayerData = {}

local sessionId = if game.JobId ~= "" then game.JobId else HttpService:GenerateGUID(false)

local function openStore(): any
	if RunService:IsStudio() then
		return SessionStore.MemoryStore.new()
	end
	local ok, store = pcall(function()
		return DataStoreService:GetDataStore(STORE_NAME)
	end)
	if ok then
		return store
	end
	warn("[PlayerData] DataStore unavailable:", store)
	return nil
end

local backing = openStore()
local sessions = if backing then SessionStore.new(backing, sessionId, os.time) else nil

local function key(userId: number): string
	return "player_" .. tostring(userId)
end

-- Returns the player's state, or nil if it could not be loaded safely.
function PlayerData.load(userId: number): Economy.State?
	if sessions == nil then
		return nil
	end
	for attempt = 1, LOAD_ATTEMPTS do
		local result, data = sessions:load(key(userId))
		if result == "loaded" then
			return Economy.sanitize(data)
		elseif result == "new" then
			return Economy.newState()
		elseif result == "corrupt" then
			warn("[PlayerData] unreadable profile for", userId)
			return nil
		end
		-- "locked": another server is still saving; "failed": transient error.
		warn(string.format("[PlayerData] load %s (attempt %d)", result, attempt))
		task.wait(if result == "locked" then LOCKED_RETRY_SECONDS else 2 ^ attempt)
	end
	return nil
end

function PlayerData.save(userId: number, state: Economy.State, release: boolean): boolean
	if sessions == nil then
		return false
	end
	local snapshot = { cash = state.cash, carried = state.carried, level = state.level }
	local profileKey = key(userId)
	local token = sessions:beginSave(profileKey)
	for attempt = 1, SAVE_ATTEMPTS do
		local result = sessions:save(profileKey, snapshot, release, token)
		if result == "saved" or result == "superseded" then
			return true
		elseif result == "lost_session" then
			warn("[PlayerData] another server owns this profile; not saving", userId)
			return false
		end
		warn(string.format("[PlayerData] save failed (attempt %d)", attempt))
		task.wait(attempt)
	end
	return false
end

return PlayerData
