# Lithium

External CS2 ESP. Read-only. Python + Qt overlay. No injection, no DLL, no driver.

## Features

- **Box ESP** — team-colored rectangles
- **Skeleton ESP** — full bone chain, 13 joints
- **Name ESP** — player name above each box
- **Health bar** — color shifts green → red
- **Armor bar** — blue, next to health
- **Distance** — meters below each player
- **Snaplines** — from screen bottom to each player
- **Head dot** — circle on the head bone
- **Bomb timer** — plant countdown + live defuse timer
- **Team ESP** — toggle teammates on/off
- **Menu** — dark panel, INSERT to open, F1 to toggle
- **Config** — saved to `options.json`, per-user

## How it works

- attaches to `cs2.exe` via `pymem`
- pulls offsets live from [a2x/cs2-dumper](https://github.com/a2x/cs2-dumper) on every launch — always current, no manual updates
- reads the entity list → controllers → pawns → bone matrices
- projects world coordinates to screen via the game's view matrix
- draws via a topmost click-through Qt window — **no hook, no injection**

## Install

\`\`\`cmd
pip install pymem pywin32 pyside6 requests
\`\`\`

## Run

\`\`\`cmd
cd Lithium-external esp
py run.py
\`\`\`

Run as **administrator**. CS2 open, in a match. Press INSERT to open the menu.

## Hotkeys

| key | action |
|---|---|
| INSERT | toggle menu |
| F1 | toggle ESP on/off |

## Build the exe

\`\`\`cmd
pip install nuitka ordered-set zstandard
python -m nuitka --standalone --onefile --windows-console-mode=disable ^
  --enable-plugin=pyside6 --include-package=Lithium --include-package=pymem ^
  --include-package=win32gui --include-package=win32api --include-package=win32con ^
  --include-package=win32com --output-dir=dist --output-filename=Lithium.exe ^
  --assume-yes-for-downloads run.py
\`\`\`

Output: `dist\Lithium.exe`. Self-contained — no Python needed on the target.

## Layout

\`\`\`
Lithium-external esp/
├── run.py              entry point
└── Lithium/
    ├── __init__.py
    ├── Overlay.py      window, menu, canvas
    ├── ESP.py          memory reads, entity walk
    ├── Offsets.py      offset table (auto-pull)
    ├── Config.py       settings persistence
    └── Entity.py       data class
\`\`\`

## Notes

- offsets auto-update from a2x on every launch — needs internet for the first run
- config lives in `Lithium/options.json`
- external topmost window — no code touches the game process except `ReadProcessMemory`
- PyInstaller/Nuitka exes will get flagged by AV — that's normal for packed binaries

## License

MIT
