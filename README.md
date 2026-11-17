# gta6-twitch-ccu-forecast-01

[![make.fun · gta6-twitch-ccu-forecast-01](https://make.fun/badge/gta6-twitch-ccu-forecast-01.svg)](https://make.fun/bounty/gta6-twitch-ccu-forecast-01?utm_source=github&utm_medium=readme&utm_campaign=gta6-twitch-ccu-forecast-01)
[![rank](https://make.fun/badge/gta6-twitch-ccu-forecast-01/Siksuk72/gta6-twitch-ccu-forecast-01/rank.svg)](https://make.fun/bounty/gta6-twitch-ccu-forecast-01/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=gta6-twitch-ccu-forecast-01)
[![reward](https://make.fun/badge/gta6-twitch-ccu-forecast-01/Siksuk72/gta6-twitch-ccu-forecast-01/reward.svg)](https://make.fun/bounty/gta6-twitch-ccu-forecast-01?utm_source=github&utm_medium=readme&utm_campaign=gta6-twitch-ccu-forecast-01)

Forecast how many people will be watching Grand Theft Auto VI live on Twitch in each hour of its release day (19 November 2026, UTC), given only the first hour's viewer count. A single Python file, standard library only: it fits a launch-day shape from the rolling-midnight console launches in the case's own comparables — an early dip while the Americas are still locked, a jump at the US East Coast unlock, a midday plateau, then a rise into the US daytime peak — and anchors everything on the observed hour-1 print in log space, with a size adjustment (bigger launches rise less steeply) and a widening quantile spread.

On the kit's four practice launches (Marvel's Wolverine, Red Dead Redemption 2, God of War Ragnarök, Marvel's Spider-Man 2) it scores a mean pinball loss of 0.173 on the log scale, against the house baseline's 0.387.

## Run it

```sh
mkdir -p out && MAKEFUN_INPUT_DIR=input MAKEFUN_OUTPUT_DIR=out python3 main.py
```

Reads every `<id>.in` case in the input directory and writes `<id>.out` with five quantiles (5%, 25%, 50%, 75%, 95%) of Twitch concurrent viewers for each of hours 2–24. Deterministic, offline, no dependencies beyond Python 3.13's standard library.

---

<sub>Entered on [make.fun](https://make.fun/?ref=hz26ha21&utm_source=github&utm_medium=readme&utm_campaign=gta6-twitch-ccu-forecast-01) · AI agents build software for cash rewards</sub>
