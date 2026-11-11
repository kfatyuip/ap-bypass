# AP-Bypass

CLI tool to bypass AP (Access Point) isolation on Linux/Android.

## Usage

```bash
sudo ./bypass_ap_isolation.py
```

or, after installation:

```bash
ap-bypass
```

## Features

- Detects default gateway and network interfaces
- Adds custom routes to bypass AP isolation for local subnet traffic
- Uses standard `ip` command for route manipulation

## Requirements

- Linux with `ip` command
- Root or sudo privileges

## Installation

```bash
uv sync
```

## License

MIT
