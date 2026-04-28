# Desktop installer (Tauri)

Builds a real native installer (`.msi` on Windows, `.dmg` on macOS, `.deb`/`.AppImage` on Linux) that bundles:
- the React frontend
- a PyInstaller-built Python sidecar that runs the FastAPI service

## Prerequisites

- Rust toolchain — install from https://rustup.rs
- Node 20+
- Python 3.10+ with `pyinstaller`
- Platform-specific Tauri prerequisites — see https://tauri.app/start/prerequisites/

## Build the Python sidecar

The Tauri app spawns `binaries/nhlsb-server` as a subprocess. Build it with PyInstaller:

```bash
cd ../backend
pyinstaller --onefile --name nhlsb-server-<TARGET-TRIPLE> \
  --collect-all nhlsb \
  src/nhlsb/__main__.py

# Copy into Tauri resource folder
mkdir -p ../desktop/src-tauri/binaries
cp dist/nhlsb-server-* ../desktop/src-tauri/binaries/
```

`<TARGET-TRIPLE>` examples:
- Windows x64: `x86_64-pc-windows-msvc.exe`
- macOS Apple Silicon: `aarch64-apple-darwin`
- macOS Intel: `x86_64-apple-darwin`
- Linux x64: `x86_64-unknown-linux-gnu`

## Build the installer

```bash
cd src-tauri
cargo tauri build
```

Output:
- Windows: `target/release/bundle/msi/NHL Scoreboard Studio_1.0.0_x64_en-US.msi`
- macOS:   `target/release/bundle/dmg/NHL Scoreboard Studio_1.0.0_aarch64.dmg`
- Linux:   `target/release/bundle/deb/nhlsb-desktop_1.0.0_amd64.deb`

## Run in dev (no installer build)

From the project root, start backend and frontend separately:

```bash
# Terminal 1
cd backend && uvicorn nhlsb.main:app --reload

# Terminal 2
cd frontend && npm run dev
```

Open http://localhost:5173 — Vite proxies `/api` and `/ws` to the backend.
