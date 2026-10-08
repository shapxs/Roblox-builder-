--!strict
-- Session-locked profile storage over any store with DataStore-style UpdateAsync.
--
-- Record shape: { data = <profile>, session = { id, at } | nil, version = n }
--
-- Rules that protect real progress:
--   * load claims the profile for this server; a profile held by another live server
--     is "locked" and is not taken (the other server may still save newer data);
--   * a failed load is never treated as a new player, so defaults are never saved
--     over a profile that could not be read;
--   * save only writes while this server still owns the session ("lost_session"
--     otherwise), so an overlapping server cannot overwrite newer progress.
--
-- Pure Luau: no Roblox globals, so Lune tests can inject failing and racing stores.

local SessionStore = {}
SessionStore.__index = SessionStore

export type LoadResult = "loaded" | "new" | "locked" | "failed" | "corrupt"
export type SaveResult = "saved" | "lost_session" | "failed"

local STALE_AFTER_SECONDS = 600 -- a lock this old belongs to a crashed server

function SessionStore.new(store: any, sessionId: string, clock: () -> number)
	return setmetatable({ store = store, sessionId = sessionId, clock = clock }, SessionStore)
end

function SessionStore.load(self: any, key: string): (LoadResult, any)
	local result: LoadResult = "failed"
	local ok, record = pcall(function()
		return self.store:UpdateAsync(key, function(old: any): any
			if old ~= nil and type(old) ~= "table" then
				result = "corrupt"
				return nil -- cancel: never overwrite what we cannot read
			end
			local session = old and old.session
			if
				session
				and session.id ~= self.sessionId
				and self.clock() - (session.at or 0) < STALE_AFTER_SECONDS
			then
				result = "locked"
				return nil
			end
			result = if old and old.data ~= nil then "loaded" else "new"
			return {
				data = old and old.data,
				session = { id = self.sessionId, at = self.clock() },
				version = (old and old.version) or 0,
			}
		end)
	end)
	if not ok then
		return "failed", nil
	end
	if result == "loaded" or result == "new" then
		return result, record and record.data
	end
	return result, nil
end

function SessionStore.save(self: any, key: string, data: any, release: boolean): SaveResult
	local result: SaveResult = "failed"
	local ok = pcall(function()
		self.store:UpdateAsync(key, function(old: any): any
			if type(old) ~= "table" or not old.session or old.session.id ~= self.sessionId then
				result = "lost_session"
				return nil
			end
			result = "saved"
			return {
				data = data,
				session = if release then nil else { id = self.sessionId, at = self.clock() },
				version = (old.version or 0) + 1,
			}
		end)
	end)
	if not ok then
		return "failed"
	end
	return result
end

-- In-memory store with the same UpdateAsync contract (Studio playtests, tests).
local MemoryStore = {}
MemoryStore.__index = MemoryStore

function MemoryStore.new()
	return setmetatable({ rows = {} :: { [string]: any } }, MemoryStore)
end

function MemoryStore.UpdateAsync(self: any, key: string, transform: (any) -> any): any
	local new = transform(self.rows[key])
	if new ~= nil then
		self.rows[key] = new
	end
	return new
end

SessionStore.MemoryStore = MemoryStore

return SessionStore
