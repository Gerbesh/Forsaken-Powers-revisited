# Forsaken Powers Revisited

**Forsaken Powers Revisited** is a clean, server-safe and honest rework of the classic Forsaken Powers mods for Valheim.

This mod focuses on **fair gameplay**, **server authority**, and **minimal dependencies**, while preserving all the QoL features players expect.

![Icon](https://raw.githubusercontent.com/Gerbesh/Forsaken-Powers-revisited/main/icon.png)

---

## Core Features

- Cycle available Forsaken Powers using hotkeys
- Reset Forsaken Power cooldowns via hotkey
- Optional activation of **all unlocked powers at once** (server-side only)
- Strict boss kill validation using **ZoneSystem global keys**
- Fully configurable cooldowns and durations
- Passive mode support
- Customizable player messages (select / reset / blocked / none available)
- **No external sync libraries required**
- Server-authoritative logic (safe for public servers)

---

## What Makes This Version Different

This mod is not just another fork - it deliberately fixes long-standing issues present in other implementations.

### Key Differences

- **Boss-based lock is enforced**
  - Powers are available **only if the corresponding boss was actually defeated**
  - No client-side bypasses
- **Server-side multi-activation**
  - Alt-key activation applies all unlocked powers **only from the server**
  - Prevents client-side cheating
- **No ServerSync / ConfigSync**
  - Lower dependency count
  - Fewer mod conflicts
- **More granular messages**
  - Separate messages for:
    - Power selected
    - Cooldown reset
    - Power blocked
    - No powers unlocked

This makes Forsaken Powers Revisited ideal for:
- Vanilla+ playthroughs
- Public or semi-public servers
- Coop worlds where fairness matters

---

## Inspirations & Credits

This mod is inspired by the following projects:

- **Forsaken Powers Plus** by *TastyChickenLegs*  
  https://thunderstore.io/c/valheim/p/TastyChickenLegs/ForsakenPowersPlus/

- **Forsaken Powers Plus Remastered** by *turbero*  
  https://thunderstore.io/c/valheim/p/turbero/ForsakenPowersPlusRemastered/

### How Forsaken Powers Revisited Differs

- Enforces boss progression strictly (no early access)
- Server-only execution for multi-power activation
- No external config sync dependencies
- Focus on security, stability and honest gameplay

This project exists to provide a **safe and fair alternative**, not to replace or discredit the original mods.

---

## Requirements

- Valheim
- BepInEx 5.x
- Harmony

---

## Installation

1. Install BepInEx for Valheim
2. Extract this mod into:
3. Launch the game once to generate config files

---

## Support & Community

<p align="center"></p>
<h2>For questions, feedback or bug reports find Gerbesh in the Odin Plus Team on Discord:</h2>
<p></p>
<p align="center">
<a href="https://discord.gg/mbkPcvu9ax">
 <img src="https://noobtrap.eu/images/crystallights/oplusdisc.png">
</a>
</p>

If you encounter bugs, have feature requests or need help:
- Write directly on Discord
- I respond quickly and actively maintain this mod

---

## License

MIT
