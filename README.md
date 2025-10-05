# Hollow Knight Gamepad Recorder

Tool-Assisted Speedrun (TAS) tool for Hollow Knight. Record and replay gamepad inputs with frame-perfect precision for Path of Pain and other challenging sections.

## Features

- **Precise recording** - Capture gamepad inputs with millisecond accuracy
- **Frame-perfect playback** - Replay through virtual gamepad (ViGEm)
- **30 recording slots** - Store multiple sequences
- **Fast combo support** - Captures rapid combinations (10-20ms)
- **Quantized inputs** - Discrete stick values for deterministic playback
- **Interference detection** - Auto-switch to recording if you take control
- **Modern UI** - Glassmorphism design with animations
- **Auto-save** - Recordings saved to JSON
- **Configurable** - Extensive JSON configuration

## Requirements

- Windows 10/11
- Python 3.8+
- Xbox-compatible gamepad
- [ViGEm Bus Driver](https://github.com/ViGEm/ViGEmBus/releases)

## Installation

1. **Install ViGEm Bus Driver**
   - Download from https://github.com/ViGEm/ViGEmBus/releases
   - Run `ViGEmBusSetup_x64.msi`
   - **Reboot your computer**

2. **Clone and install**
   ```bash
   git clone https://github.com/yourusername/hollow-knight-tas.git
   cd hollow-knight-tas
   pip install -r requirements.txt
   ```

3. **Run**
   ```bash
   python main.py
   ```

## Quick Start

1. **Record** - Press L3 (left stick click) to start recording
2. **Perform actions** - Play your sequence
3. **Stop** - Press L3 again
4. **Playback** - Press R3 (right stick click) to replay
5. **Save** - Press `S` to save recordings

## Controls

### Gamepad
- **L3** (left stick click) - Start/stop recording
- **R3** (right stick click) - Start/stop playback
- **D-pad Up/Down** - Switch slots (1-30)

### Keyboard
- **S** - Save recordings
- **L** - Load recordings
- **Q** - Quit
- **O** - Toggle overlay
- **T** - Toggle always on top
- **1-9** - Quick slot select

### Overlay
- **Drag** - Left-click and drag to move
- **Close** - Double-click
- **Menu** - Right-click for context menu
- **Animation** - Pulsing border during record/playback

## Configuration

Edit `config/user_config.json` to customize:

```json
{
  "gamepad": {
    "polling_rate": 1000,        // Polling rate (Hz)
    "stick_deadzone": 0.05,      // Stick deadzone
    "quantize_sticks": true      // Discrete stick values
  },
  "recording": {
    "max_slots": 30,
    "auto_save": true
  },
  "ui": {
    "overlay_position": "top-right",
    "theme": "dark"
  },
  "playback": {
    "enable_looping": false,
    "loop_count": -1             // -1 = infinite
  },
  "logging": {
    "level": "INFO"              // INFO or DEBUG
  }
}
```

## Troubleshooting

**Virtual gamepad not working**
- Ensure ViGEm Bus Driver is installed
- Reboot after installation
- Check logs: `gamepad_recorder.log`
- Try running as administrator (rarely needed)

**Gamepad not detected**
- Connect gamepad before starting the app
- Test in Windows Settings > Devices
- Check logs for details

**Playback doesn't match recording**
- Enable V-Sync in Hollow Knight
- Limit game FPS to 60
- Close resource-intensive apps
- Increase `polling_rate` to 1000

**Recording too large**
- Increase `stick_deadzone` (filters hand tremor)
- Set `quantize_sticks: true`
- Record shorter sequences

## How It Works

1. **Recording**: Captures all gamepad state changes with precise timestamps
2. **Quantization**: Converts analog sticks to discrete -1.0/0.0/1.0
3. **Playback**: Uses ViGEm virtual gamepad to replay at exact times
4. **Optimization**: 1000 FPS polling for ~1ms latency

## Known Limitations

- Unity's non-deterministic physics may cause 1-3 pixel variations
- Best for: Short sequences, frame-perfect combos
- Not ideal for: Long full-level runs requiring pixel-perfect positioning

## Project Structure

```
hollow-knight-tas/
├── main.py                    # Entry point
├── config/
│   ├── default_config.json
│   └── user_config.json
├── src/recorder/
│   ├── gamepad_recorder.py
│   ├── gamepad_state.py
│   ├── virtual_gamepad.py
│   └── sequence_manager.py
└── recordings/
    └── sequences.json
```

## License

MIT License

## Acknowledgments

- [ViGEm](https://github.com/ViGEm/ViGEmBus) for virtual gamepad driver
- Hollow Knight speedrunning community
