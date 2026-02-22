# Cemu Controller Profile Extension

Programmatic API for managing Cemu 2.6 controller profiles from Python.
Part of the Meridian emulator extensions framework.

## Installation

No extra dependencies — the extension uses only the Python standard library.
It lives at `emulators/extensions/cemu/` and is importable from the Meridian
project root.

## Quick Start

```python
from emulators.extensions.cemu import (
    create_profile,
    save_profile,
    load_profile,
    list_profiles,
    import_profile,
    delete_profile,
    apply_profile_to_game,
    MappingEntry,
)

# Create a profile from scratch
profile = create_profile(
    name="MyProfile",
    emulated_type="Wii U GamePad",
    api="SDLController",
    uuid="0",
    display_name="DualSense Wireless Controller",
    rumble=0.5,
    motion=True,
    axis_deadzone=0.15,
    trigger_deadzone=0.25,
    mappings={
        1: 1,    # A -> SDL button 1
        2: 0,    # B -> SDL button 0
        3: 3,    # X -> SDL button 3
        4: 2,    # Y -> SDL button 2
        7: 42,   # ZL -> Left trigger (kTriggerXP)
        8: 43,   # ZR -> Right trigger (kTriggerYP)
    },
)

# Save to a Cemu installation
cemu_dir = "path/to/cemu"
save_profile(profile, cemu_dir)

# List all profiles
names = list_profiles(cemu_dir)

# Load a profile back
loaded = load_profile(cemu_dir, "MyProfile")

# Import an existing XML file
imported = import_profile("path/to/exported.xml", cemu_dir)

# Delete a profile
delete_profile(cemu_dir, "MyProfile")
```

## Mapping IDs

Cemu uses numeric IDs (1–27) for emulated controller buttons on the Wii U
GamePad.  The extension exposes named constants:

| ID | Constant | Button |
|----|----------|--------|
| 1 | `MAPPING_A` | A |
| 2 | `MAPPING_B` | B |
| 3 | `MAPPING_X` | X |
| 4 | `MAPPING_Y` | Y |
| 5 | `MAPPING_L` | L |
| 6 | `MAPPING_R` | R |
| 7 | `MAPPING_ZL` | ZL |
| 8 | `MAPPING_ZR` | ZR |
| 9 | `MAPPING_PLUS` | + |
| 10 | `MAPPING_MINUS` | − |
| 11 | `MAPPING_HOME` | Home |
| 12 | `MAPPING_DPAD_UP` | D-Pad Up |
| 13 | `MAPPING_DPAD_DOWN` | D-Pad Down |
| 14 | `MAPPING_DPAD_LEFT` | D-Pad Left |
| 15 | `MAPPING_DPAD_RIGHT` | D-Pad Right |
| 16 | `MAPPING_LSTICK_DOWN` | L-Stick Down |
| 17 | `MAPPING_LSTICK_UP` | L-Stick Up |
| 18 | `MAPPING_LSTICK_LEFT` | L-Stick Left |
| 19 | `MAPPING_LSTICK_RIGHT` | L-Stick Right |
| 20 | `MAPPING_RSTICK_DOWN` | R-Stick Down |
| 21 | `MAPPING_RSTICK_UP` | R-Stick Up |
| 22 | `MAPPING_RSTICK_LEFT` | R-Stick Left |
| 23 | `MAPPING_RSTICK_RIGHT` | R-Stick Right |
| 24 | `MAPPING_LSTICK_PRESS` | L-Stick Press |
| 25 | `MAPPING_RSTICK_PRESS` | R-Stick Press |

## Button Encoding (Buttons2)

The `<button>` value in Cemu XML is a uint64 from the Buttons2 enum:

- **0–31**: Direct SDL GameController button indices
- **32**: `BUTTON_ZL` — ZL trigger as a button
- **33**: `BUTTON_ZR` — ZR trigger as a button
- **34–37**: D-pad (Up, Down, Left, Right)
- **38–43**: Axis positive (LeftX, LeftY, RightX, RightY, TriggerL, TriggerR)
- **44–49**: Axis negative (same order)

The `SDL_AXIS_TO_BUTTONS2` dict maps SDL axis indices to `(positive, negative)`
pairs for easy conversion.

## Meridian Integration

### Adapter: Meridian Settings → Cemu Profiles

```python
from emulators.extensions.cemu import (
    meridian_player_to_cemu,
    meridian_players_to_cemu,
    cemu_to_meridian_bindings,
    save_profile,
    apply_profile_to_game,
)

# Convert a single Meridian player dict
player_data = {
    "connected": True,
    "api": "Auto",
    "device": "DualSense Wireless Controller",
    "device_index": 0,
    "type": "Wii U GamePad",
    "bindings": {
        "a": "Button 1",
        "b": "Button 0",
        "zl": "Axis 4-",
        "ls_up": "Axis 1-",
        # ... all bindings
    },
}
profile = meridian_player_to_cemu(player_data, profile_name="meridian_player1")
save_profile(profile, cemu_dir)

# Convert all players at once
all_players = {"1": player_data, "2": {...}, ...}
profiles = meridian_players_to_cemu(all_players)
for idx, prof in profiles.items():
    save_profile(prof, cemu_dir)

# Assign profiles to a specific game
apply_profile_to_game(
    title_id="0005000010143500",
    player_profiles={1: "meridian_player1"},
    cemu_dir=cemu_dir,
)

# Convert back: Cemu profile → Meridian bindings
bindings = cemu_to_meridian_bindings(profile)
# {"a": "Button 1", "b": "Button 0", "zl": "Axis 4-", ...}
```

### Auto-Configuration at Launch

When Meridian launches a Wii U game through Cemu, the extension is called
automatically from `meridian/core/emulator_setup.py`.  It:

1. Reads Meridian's active player settings
2. Converts each connected player to a Cemu profile via the adapter
3. Saves profiles to Cemu's `controllerProfiles/` directory
4. Optionally assigns profiles to the launched game's `gameProfiles/*.ini`

## Cemu Directory Layout

```
cemu/
├── Cemu.exe
├── portable/
│   ├── controllerProfiles/   ← profiles go here (portable mode)
│   │   ├── meridian_player1.xml
│   │   └── ...
│   └── settings.xml
├── controllerProfiles/       ← fallback location
├── gameProfiles/
│   └── 0005000010143500.ini  ← per-game controller assignments
└── keys.txt
```

## Running Tests

```bash
python -m pytest emulators/extensions/cemu/tests/ -v
```
