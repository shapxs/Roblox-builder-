# ForgeQA test place

Local-only, deliberately empty Studio place Forge tests games in
(`roblox.qa_studio_name: ForgeQA`). Every Forge game builds its own ground, spawn and
stations in code; anything pre-placed here would sit in the game's world (a baseplate
once buried every station and made all prompts unreachable).
Never publish it, and never keep a published (staging/production) place open in Studio:
an open session locks the place against API publishes (HTTP 409).

Rebuild: `~/.rokit/tool-storage/rojo-rbx/rojo/7.7.1/rojo build default.project.json -o ../ForgeQA.rbxl`
