# ForgeQA test place

Local-only Studio place Forge tests games in (`roblox.qa_studio_name: ForgeQA`).
Never publish it, and never keep a published (staging/production) place open in Studio:
an open session locks the place against API publishes (HTTP 409).

Rebuild: `~/.rokit/tool-storage/rojo-rbx/rojo/7.7.1/rojo build default.project.json -o ../ForgeQA.rbxl`
