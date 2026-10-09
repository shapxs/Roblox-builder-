# atmosphere kit

Named lighting moods (day, sunset, twilight, night, spooky, underwater) with real volumetric fog (Atmosphere instance), colour grading, and blending for day/night cycles.

Module: `ReplicatedStorage.Shared.Kits.Atmosphere`

```lua
Atmosphere.apply(Lighting, "twilight")  -- or a preset table
Atmosphere.blend("day", "night", t) -> preset  -- for day/night cycles
Atmosphere.Presets.<name>  -- data you can copy and tweak; Atmosphere.validate(preset)
```
