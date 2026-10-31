# VW-APP-GAME - game data sources for the companion app

Status: DONE 2026-10-31. All sources below were read or probed on 2026-10-31.
Every row names its charter class (`docs/companion-app.md` section 3, classes
1-4). A source with no class is not used. Ports and other write-capable
channels carry a ruling ref. Per R-APP-4, the app's poll rate for each
source is AT MOST the "app rate" column, which sits well under the
published limit. Every poll backs off on 429 / 503 / 504 and honours
`Retry-After`.

## Class 1 - public / official web APIs

### Community Deadlock API (`https://api.deadlock-api.com`)

- Spec: OpenAPI 3 at `https://api.deadlock-api.com/openapi.json` (v0.1.0,
  about 140 paths). Code license MIT (`github.com/deadlock-api/deadlock-api`).
  The service is not endorsed by Valve and says so in its own disclaimer.
  The data it serves (hero / item KV3 values, match metadata) is Valve game
  data, so the code license does not cover redistributing it (see
  VW-APP-HERO, decision D-HERO-1).
- Auth: optional key in the `X-API-KEY` header (or `api_key` query). A key
  raises some limits. A key is never tracked: it lives in app user data or an
  env var, like every secret here.
- Caching: asset responses send `Cache-Control: public, max-age=3600,
  stale-while-revalidate=7200` and `Last-Modified`, so the app sends
  If-Modified-Since. Analytics results are cached server-side for 1 h, so
  polling an identical query faster than 1 h gains nothing.
- Load shedding: an uncached DB query can fail `503` + `Retry-After`. A
  time-limit hit fails `504`, then fails fast for minutes. The app narrows
  its filters and does not retry the identical request.

Endpoints the app uses, with the published per-IP limit and the app's
ceiling:

- `GET /v1/assets/heroes`, `/v1/assets/heroes/{id}`: per-patch hero
  metadata from KV3 (id, class_name, name, hero_type, starting_stats,
  level_info, scaling_stats, standard_level_up_upgrades, items, tags). Limit
  not published (CDN cached). App rate: on a new client version, else 1/24 h.
  Feeds E1 and VW-APP-HERO.
- `GET /v1/assets/items` (and the `by-type`, `by-slot-type`, `by-hero-id`
  variants): 782 entries at the latest client version, 6836 - 437 ability, 250 upgrade,
  95 weapon. Fields: id, class_name, name, type, item_slot_type, item_tier,
  cost, is_active_item, properties{value, scale_function, label, ...},
  upgrades, weapon_info, tooltip_sections. App rate: same as heroes. Feeds E1.
- `GET /v1/assets/client-versions`: the list of client build numbers. It is
  the patch key for every dataset and distilled rule (R-COACH-3). App rate:
  1/1 h while the app runs, 0 in a match.
- `GET /v2/patches`: one feed from the official changelog forum RSS and the
  Steam news feed (source, title, pub_date, link, content). Published limit
  100 req/s. App rate: 1/1 h, 0 in a match. It triggers the patch re-review
  of R-COACH-3.
- `GET /v1/players/{account_id}/match-history`: the player's match list.
  Published limits: stored history 100 req/s, bot-friend refresh 10 req/h,
  `force_refetch` 1 req/h. App rate: 1 call after a match ends plus 1 per app
  start, never `force_refetch` on a timer. Feeds E2. The account id is the
  operator's own, held in app user data, never tracked.
- `GET /v1/matches/{match_id}/metadata`: post-match detail (players, items
  bought with times, stats over time, objectives). Published: cache 100 req/s,
  S3 100 req/10 s, Steam fallback 3 req/h. App rate: once per new own match,
  results stored in the local DB and never fetched twice. Class 2 data
  served over class 1.
- `GET /v1/analytics/*` (hero-stats, item-stats, hero-counter-stats,
  hero-synergy-stats, build-item-stats, item-permutation-stats,
  lane-matchup-stats, ...): aggregate win rates and builds. The published
  200 req/min per IP is shared by all analytics endpoints. App rate: a fixed
  query set refreshed at most 1/6 h, outside matches only. Feeds E1 counters
  and E3 priors.
- `GET /v1/builds`: community builds. Published 100 req/s. App rate: on
  demand from the dashboard, pre-match only.
- `GET /v1/patches` (deprecated; replaced by v2), `/v1/assets/ranks`,
  `/v1/assets/map`, `/v1/assets/npc-units`, `/v1/assets/modifiers`: static
  reference data, refreshed with the client version.
- `GET /v1/assets/convars`: every cvar in the patch's client / server dll
  with its `FCVAR_*` flags. NOT used by the app; noted for VW's autoexec
  tooling: `tools/vw_cvar_check.py` (VW-CVAR-CHECK, 2026-10-31) caches it
  with `fetch` and flags cheat (bit 14) / development-only (bit 1) cvars.
  Patch 6836: 3499 cvars; engine2 cvars (`fps_max`, `rate`, ...) are absent.

Endpoints NOT used, each with its ruling:

- `GET /v1/matches/{match_id}/live/url`, `/v1/matches/live/urls`,
  `/v1/matches/demo/live/query`: they spectate a LIVE match through a bot
  and return the broadcast URL. Ruling G-1 (below): never for a match the
  operator is in.
- `POST /v1/matches/custom/*` (create / ready / start / leave a lobby):
  actions in the game coordinator, not data. Ruling G-2: not used.
- `POST /v1/matches/salts`, `POST /v1/feedback`, `/v1/patron/*`: these send
  data outward or manage the service's bot friends. Ruling G-3: the app only
  issues GETs (plus read-only query POSTs below) and uploads nothing.
- `GET/POST /v1/sql`, `POST /v1/graphql`, `POST /v1/matches/demo/query`:
  read-only query surfaces (published: sql 2 req/min and 20 req/h per IP;
  graphql 300 req/min; demo query 200 req/h, about 55 s per job). Allowed for
  dashboard research only, with the rates above, never polled.

### Steam Web API (`https://api.steampowered.com`)

- `ISteamNews/GetNewsForApp/v2?appid=1422450`: answered 200, keyless. App
  rate 1/1 h. It overlaps `/v2/patches`, so it is a fallback only.
- `ISteamUserStats/GetNumberOfCurrentPlayers/v1?appid=1422450`: answered
  `{"result":42}` (no match) on 2026-10-31, so there is no player count for
  this app. Not used.
- `ISteamUser/GetPlayerSummaries` (needs a key): the operator's display name
  and avatar for the dashboard. App rate: 1 per app start. The key is never
  tracked.
- Store `appdetails` (keyless): app metadata. Used only by the S-6 Workshop
  re-check (`docs/research/workshop.md`).

### Valve published text

- Changelog forum RSS `https://forums.playdeadlock.com/forums/changelog.10/index.rss`
  and the Steam news page: patch notes, read through `/v2/patches` (above).
- Valve developer wiki, "List of Deadlock console commands and variables":
  reference only.

## Class 2 - post-match data and replays

- Match metadata, as above (`/v1/matches/{id}/metadata`).
- Replay demo files: `/v1/matches/{id}/salts` returns cluster_id and
  replay_salt for a finished match (published: DB 100 req/s, Steam fallback
  3 req/h). The demo is Valve's replay download, a bz2 `.dem` of a few
  hundred MB. The app downloads one only on demand for the operator's own
  match, parses it outside the game, and deletes the raw file after
  extraction (repo and disk budget). Parser candidates named by the API:
  demofile-net (C#), haste (Rust). Choosing one is a VW-APP-SEC
  supply-chain item.
- In-game replays the client itself downloads: read-only if the client keeps
  them on disk. The path is not confirmed yet (a read-only probe in
  VW-APP-INGEST).

## Class 3 - the game's own outputs (read-only)

- `<Deadlock>/game/citadel/cfg/autoexec.cfg`: VW owns it (floor list).
- The video settings file the game owns: read, plus the menu's own keys
  written per the floor.
- Key bindings and cfg under `<Deadlock>/game/citadel/cfg/`: read-only.
- Steam `userdata/<id>/1422450/remote/`: read and backup only (floor).
- Steam `localconfig.vdf`: launch options are read. They are written only
  while Steam is down (floor).
- Console log: `-condebug` is the Source launch option that writes the
  console to `console.log`. The Valve wiki notes that Deadlock's
  `-condebug` does not capture `cvarlist` output as older games did, so
  whether it writes `game/citadel/console.log` at all is unconfirmed. Next
  step: a read-only existence probe after the operator next plays with the
  option (proposed item VW-APP-CONLOG). If the file exists, it is the S-5
  alternative for live events (deaths, purchases if logged), read-only and
  tailed by offset.
- Game state integration (`gamestate_integration_*.cfg`): S-7. No evidence
  was found that Deadlock supports it, and the cfg would in any case be a
  game file outside the floor's list. Not written.

## Class 4 - screen capture of the operator's display

- Windows Graphics Capture (window or monitor) or DXGI desktop duplication,
  per S-3. It is the only LIVE in-match source: HUD reads (souls, HP,
  timers) through CV in a separate process. OBS Game Capture is forbidden.
  Details belong to the VW-APP-INGEST epic.

## Launch options and ports

- `-netconport <port>`: ruling S-5. NOT used. It opens a TCP console that
  accepts commands, which makes it a write channel into the game.
- `-condebug`: class 3 output, see above. It is a launch option the game
  exposes, so adding it follows the floor's localconfig rule (only while
  Steam is down, or recorded for the operator).
- `-dev`, `-console`: player-facing console toggles, no data value. VW
  already manages launch options in `config/launch_options.txt`.
- No HTTP or other listening port of the game client is used.

## Rulings made here (adjudicated 2026-10-31)

- G-1 Live spectate of the operator's own match: NEVER. Decision: the
  live-broadcast endpoints are used for no match the operator is in, and
  none while any own match is live. Alternatives: (a) use the live feed for
  E3 - rejected, because it gives information the player's client does not
  show (ghosting, the same class of harm as a memory reader); (b) use it
  with a delay - rejected, any in-match use is still outside-information
  advice. Why: the floor's intent (no competitive information beyond the
  game's own UI) and S-1's live gap belong to class 4 CV. Allowed use: none
  in v1; an ended match uses post-match data. Reverses: never for an own
  live match.
- G-2 Lobby control (`/v1/matches/custom/*`): NOT used. Decision: no lobby
  action. Alternatives: automate custom practice lobbies - rejected, because
  it acts in the game coordinator through someone else's bot accounts.
  Why: the app is read-only toward the game and Valve services. Reverses:
  an operator amendment naming the feature.
- G-3 Outbound data (salts ingest, feedback, patron): NOT used. Decision:
  the app uploads nothing. Alternatives: contribute salts to help the API -
  rejected for privacy (it sends own match ids and a user-agent). Why:
  privacy, and an app that only reads is simpler to audit (VW-APP-SEC).
  Reverses: an explicit operator opt-in setting, default off.

## Sources (read 2026-10-31)

- `https://api.deadlock-api.com/openapi.json` (paths, limits, load-shedding text)
- `https://api.deadlock-api.com/v1/assets/heroes`, `/v1/assets/items`,
  `/v1/assets/client-versions`, `/v2/patches`, `/v1/info`
- `https://live.deadlock-api.com/docs/api` (429 + `Retry-After`)
- `https://api.steampowered.com/ISteamNews/GetNewsForApp/v2/?appid=1422450`
- `https://api.steampowered.com/ISteamUserStats/GetNumberOfCurrentPlayers/v1/?appid=1422450`
- `https://developer.valvesoftware.com/wiki/List_of_Deadlock_console_commands_and_variables`
- `https://forums.playdeadlock.com/forums/changelog.10/index.rss`
