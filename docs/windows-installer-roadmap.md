# Windows Installer Roadmap

The current portable package is a release ZIP because it is transparent, easy to inspect, and avoids bundling secrets. A Windows `.exe` installer is possible as a later distribution phase.

## Recommended Architecture

Use a desktop shell plus local backend:

- Frontend shell: Tauri or Electron.
- Backend executable: FastAPI bundled with PyInstaller.
- Local persistence: SQLite for desktop mode, with PostgreSQL still supported for developer/server mode.
- Runtime: desktop app starts the backend on `127.0.0.1` and opens the bundled frontend shell.
- Secrets: API keys are stored in a local user config file or OS credential store, never bundled into the installer.

## Tauri vs Electron

Tauri is usually smaller and faster to install because it uses the system WebView. It needs Rust tooling but produces compact installers.

Electron is heavier but very mature for Node/React apps and has a familiar packaging ecosystem.

For this app, Tauri is the cleaner long-term product direction, while Electron may be easier if you want the fastest prototype.

## Will An EXE Make Local Loading Faster?

Not automatically. An installer mainly improves startup convenience. It can feel faster if it:

- Runs a production-built frontend instead of `next dev`.
- Avoids cloud-sync path overhead.
- Uses a local bundled backend process.
- Uses SQLite for local desktop mode.
- Warms demo caches on launch.

The biggest speed win is moving from Next.js dev mode to a production build, not the `.exe` file itself.

## Packaging Phases

1. Add a desktop mode config profile.
2. Build the frontend as static or standalone assets.
3. Bundle the FastAPI backend with PyInstaller.
4. Add a launcher that starts/stops the backend safely.
5. Store keys in user-local config and keep them out of installer artefacts.
6. Build signed Windows installer with Tauri bundler, NSIS, or WiX.
7. Add installer smoke tests that verify no `.env` or secrets are bundled.
