# VW-APP-WORKSHOP - does Deadlock have an official Steam Workshop?

Status: DONE 2026-10-31. Charter ruling: S-6 (`docs/companion-app.md` section 3).

## Verdict

NO. Deadlock (Steam app 1422450) has no official Steam Workshop as of
2026-10-31. Under S-6 the companion app ships no Workshop or mod integration.

## Evidence (all read 2026-10-31)

1. Workshop hub for the app: `https://steamcommunity.com/app/1422450/workshop/`
   answers HTTP 302 to the generic `https://steamcommunity.com/workshop`
   page. That is Steam's behaviour for an app with no Workshop. Controls:
   the same URL for app 570 (Dota 2) and app 730 (Counter-Strike 2) answers
   HTTP 200.
2. Store categories: `https://store.steampowered.com/api/appdetails?appids=1422450&filters=categories`
   lists only `Multi-player`. App 570 lists `Steam Workshop` among its
   categories.
3. Valve has made no Workshop or mod-support announcement in the official
   news feed (`https://store.steampowered.com/news/app/1422450`, latest post
   read: "Halloween 2026 + Gameplay Update", 2026-10-30) or the changelog
   forum (`https://forums.playdeadlock.com/forums/changelog.10/`).
4. Community modding happens outside Steam: the community mod manager
   documentation (`https://docs.deadlockmods.app/modding`) and install guides
   (e.g. `https://www.esports.net/wiki/guides/deadlock-mod-install`) describe
   VPK addons loaded by editing `gameinfo.gi`. A press report
   (`https://egw.news/deadlock/news/33719/deadlock-modder-sells-20-skin-before-valve-adds-mo-Hf77FIrfU`)
   states Valve has published no position on mods.

## Scoped ruling (S-6 applied; adjudicated 2026-10-31)

- Decision: no mod, addon or Workshop feature in the app. The app never
  reads, writes, lists or recommends VPK addons, and never touches
  `gameinfo.gi`, `game/citadel/addons/`, `bin/` or any `.vpk`.
- Alternatives: (a) integrate the community mod manager or its API - rejected,
  because VPK addons and a `gameinfo.gi` edit are files the floor forbids;
  (b) only link to mod sites - rejected, it adds nothing to E1-E3 and points
  the player at content the floor excludes.
- Why: S-6 allows only an official Workshop, and none exists. Community
  addons fall under the floor's `.vpk` exclusion whatever Valve tolerates.
- Reverses: Valve ships an official Steam Workshop for app 1422450. The
  re-check is the same two probes as evidence 1 and 2. A new ruling then
  scopes the content the game itself loads through that Workshop.
