# feedback kit

Action feedback: floating +N pop-ups, HUD bounce and flash, particle bursts, a colour palette, and number formatting.

Module: `ReplicatedStorage.Shared.Kits.Feedback`

```lua
Feedback.popup(screenGui, Feedback.delta(5), Feedback.color("reward"))  -- client
Feedback.bounce(guiObject); Feedback.flash(guiObject, color)  -- client
Feedback.burst(part, Feedback.color("magic"), 20)  -- server or client
Feedback.delta(1250) -> "+1,250"; Feedback.spread(i, n) for stacked pop-ups; palette: reward, gain, loss, info, magic
```
