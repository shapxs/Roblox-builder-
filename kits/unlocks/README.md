# unlocks kit

Qualitative progression: level-gated unlock rules, newly-unlocked detection for announcements, next-unlock hints, and showing/hiding world content tagged with an Unlock attribute.

Module: `ReplicatedStorage.Shared.Kits.Unlocks`

```lua
local RULES = Unlocks.define({ {id="glow_basket", level=5, title="Glowing basket"}, ... })
Unlocks.newly(RULES, oldLevel, newLevel) -> rules crossed (announce them)
Unlocks.isUnlocked(RULES, id, level); Unlocks.unlockedAt(RULES, level); Unlocks.nextAfter(RULES, level)
Unlocks.applyWorld(workspace, RULES, level)  -- parts/models with attribute Unlock="<id>"
```
