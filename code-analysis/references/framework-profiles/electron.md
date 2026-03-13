# Electron Framework Profile

## Detection Markers

- `package.json` with `electron` dependency
- `main.js` or `src/main/` directory with `BrowserWindow` creation
- `electron-builder.yml` or `electron-builder.json` (packaging config)
- `electron-forge` configuration in `package.json` or `forge.config.js`
- `preload.js` or `preload.ts` for context bridge scripts

## Architecture Expectations

```
src/
  main/                  # Main process (Node.js)
    index.ts             # App lifecycle, window management
    ipc/                 # IPC handler definitions
    services/            # Backend services (file I/O, DB, system)
    menu/                # Application menu definitions
  preload/               # Preload scripts (context bridge)
    index.ts             # exposeInMainWorld API definitions
  renderer/              # Renderer process (web framework)
    (standard web framework structure)
  shared/                # Types/constants shared across processes
resources/               # Static assets bundled with app
```

- Main process MUST handle: file system, native APIs, window management, system tray
- Renderer process MUST NOT have direct Node.js access (use context bridge)
- Preload scripts bridge main and renderer via `contextBridge.exposeInMainWorld`

## Common Patterns

- **Context bridge**: `contextBridge.exposeInMainWorld('api', { ... })` for secure IPC
- **IPC channels**: `ipcMain.handle()` / `ipcRenderer.invoke()` for request-response
- **Window management**: `BrowserWindow` creation with proper security defaults
- **Auto-updater**: `electron-updater` with differential updates
- **Tray integration**: `Tray` with context menu for background apps
- **Protocol handlers**: Custom `app://` protocol for local resource loading
- **Store persistence**: `electron-store` for user preferences
- **Crash reporting**: Built-in `crashReporter` or Sentry integration

## Common Anti-Patterns

- **Node integration enabled**: `nodeIntegration: true` in renderer (security risk)
- **Missing context isolation**: `contextIsolation: false` bypasses security boundary
- **Remote module usage**: `@electron/remote` gives renderer full Node.js access
- **IPC without validation**: Trusting renderer messages without input validation
- **Synchronous IPC**: `ipcRenderer.sendSync()` blocks the renderer process
- **Missing CSP**: No Content-Security-Policy on renderer pages
- **Single process everything**: All logic in main process, renderer as thin shell
- **Unbounded window creation**: No limit on `BrowserWindow` instances

## Performance Hotspots

- Memory usage: each `BrowserWindow` is a Chromium process (~50-100MB baseline)
- Startup time: large `node_modules`, missing lazy imports in main process
- IPC overhead: frequent small messages instead of batched operations
- Renderer bundle size: same concerns as web apps (tree-shaking, code splitting)
- Hidden windows consuming resources (properly hide/destroy when not needed)
- Native module compilation: `node-gyp` modules across platforms
- Auto-updater downloading full app instead of differential updates
- Missing `v8-compile-cache` or snapshot for faster startup

## Security Considerations

- **Context isolation**: MUST be enabled (`contextIsolation: true`)
- **Node integration**: MUST be disabled in renderer (`nodeIntegration: false`)
- **CSP headers**: MUST set restrictive Content-Security-Policy
- **Web security**: MUST NOT disable (`webSecurity: false` opens CORS bypass)
- **Preload validation**: Validate all IPC messages in main process handlers
- **Protocol handling**: Register custom protocols with proper scheme privileges
- **Remote content**: Validate/restrict loading of remote URLs (`will-navigate` event)
- **Dependency supply chain**: Audit npm dependencies regularly (large attack surface)
- **Permissions**: Use `session.setPermissionRequestHandler` to control web permissions
- **Fuses**: Set Electron fuses to disable dangerous runtime features

## Testing Approach

- **Main process unit**: Jest/Vitest with mocked Electron APIs
- **Renderer unit/component**: Standard web testing (Testing Library, Vitest)
- **E2E**: Playwright with Electron support or Spectron (deprecated, migrate to Playwright)
- **IPC contract tests**: Verify channel names and payload shapes match across processes
- **Packaging tests**: Verify builds on all target platforms (CI matrix)
- **Coverage**: c8/Istanbul for both main and renderer processes

## Context7 Library IDs

- `electron/electron` -- Electron framework
- `electron-userland/electron-builder` -- Packaging and publishing
- `electron/forge` -- Electron Forge toolchain
- `sindresorhus/electron-store` -- Simple data persistence
- `megahertz/electron-log` -- Logging
