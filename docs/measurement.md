# Measuring a change

A setting stays only if it is measured. No baseline exists yet: the game had
never been launched on 2026-10-25 (ROADMAP DL-MEASURE).

## Method

1. Same scene every time: Sandbox (Play > Sandbox), one hero, the same lane
   walk for 60 seconds, then a 60-second bot fight with abilities.
2. Capture with PresentMon or the NVIDIA overlay frame-time log (no tool that
   attaches to the game process; both read the OS presentation events).
3. Record: average fps, 1 percent low, 0.1 percent low, average PC latency
   (Reflex), GPU utilisation, VRAM, CPU busiest core.
4. Three runs per configuration; report the median. A change is kept when it
   improves 1 percent lows or latency without a loss elsewhere beyond run noise.
5. Results go in `docs/measurements/<date>-<topic>.md` with the config commit
   they measured.

## Order

1. Baseline: the game's own detected defaults (first launch, no autoexec).
2. Video recommendations (`config/video.recommended.json`).
3. autoexec (frame cap, frame pacing).
4. Fullscreen optimizations on vs off (flag only).
