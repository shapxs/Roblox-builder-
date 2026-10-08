# Publishing Roblox Games

Two stages, both approved in Telegram:

```text
ship (freeze commit -> test that exact copy -> card)
  -> Approve        publishes the frozen place file to your private STAGING experience
  -> Promote card   publishes the same bytes to PRODUCTION (separate approval)
```

Nothing is ever rebuilt between approval and upload. A failed upload can be retried with a
new approval; an UNKNOWN result (connection lost mid-upload) is never retried until you
have checked the place's version history.

## One-time setup per game

1. **Staging experience.** In Studio, open the game's place and use
   File → Publish to Roblox As… → *Create new experience*. Keep it private
   (Creator Dashboard → the experience → Settings → Privacy: Private).
2. **Production experience** (optional until you want players). Same as above; this is the
   public one.
3. **IDs.** Creator Dashboard → the experience → copy the **Universe ID** (also called
   Experience ID) and the start place's **Place ID**. Do this for staging and production.
4. **Destinations** go in `policy/<game_id>/publish.json` (controller-owned; a builder can
   never change where releases go):

   ```json
   {"destinations": {
     "staging":    {"universe_id": 1234567890, "place_id": 9876543210},
     "production": {"universe_id": 1234567891, "place_id": 9876543211}
   }}
   ```

   No `publish.json` = publishing off for that game (Approve just records the approval).

## One-time setup for the Mac

5. **Open Cloud API key.** create.roblox.com → Open Cloud → API Keys → Create:
   - Access permissions: **universe-places → Write**, selecting only your staging (and
     production) experiences
   - Accepted IP addresses: this Mac's public IP
   - Expiration: e.g. 90 days
6. **Store it in Keychain** (hidden prompt; never on a command line):

   ```bash
   cd ~/Voya/AutoDevFactory-roblox
   .venv/bin/python scripts/roblox_set_publish_key.py
   .venv/bin/python scripts/roblox_set_publish_key.py --check <game_id>
   ```

## Shipping

```bash
.venv/bin/python scripts/roblox_release.py ship --game <game_id> \
    --repo "~/Roblox Games" --subdir games/<game_id>
.venv/bin/python scripts/roblox_release.py status
.venv/bin/python scripts/roblox_release.py retry <release_dir>/manifest.json
```

The Telegram buttons are handled by the running Forge controller once the
`feature/roblox-studio-domain` branch is merged into it.

## What the Roblox API does not do

- It cannot create experiences: step 1 is manual by design.
- It publishes new versions of an existing place only; rollback = approve an older
  release again (it is still frozen) or use the Creator Dashboard's version history.
- Places containing EditableImage, EditableMesh, PartOperation, SurfaceAppearance or
  BaseWrap instances cannot be updated through the API (template games use none).
