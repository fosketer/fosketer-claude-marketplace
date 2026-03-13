# Tauri Framework Profile

## Detection Markers

- `src-tauri/` directory with `Cargo.toml` containing `tauri` dependency
- `src-tauri/tauri.conf.json` or `src-tauri/Tauri.toml` configuration
- `src-tauri/src/main.rs` or `src-tauri/src/lib.rs` with Tauri bootstrap
- Frontend in root or `src/` with web framework (React, Svelte, Vue, Solid)
- `package.json` with `@tauri-apps/cli` dev dependency

## Architecture Expectations

```
src-tauri/
  src/
    main.rs | lib.rs     # Tauri app bootstrap
    commands/             # IPC command handlers (#[tauri::command])
    state/                # Managed state (AppState)
    models/               # Data structures shared with frontend
    utils/                # Backend utilities
  Cargo.toml
  tauri.conf.json         # App configuration, permissions, windows
  capabilities/           # Tauri v2 capability files
  icons/                  # App icons
src/ | frontend/
  (standard web framework structure)
```

- Rust backend SHOULD handle: file I/O, system APIs, heavy computation, security-sensitive ops
- Frontend SHOULD handle: UI rendering, user interaction, display logic
- IPC boundary MUST be explicit: all Rust-to-JS communication via commands and events

## Common Patterns

- **IPC commands**: `#[tauri::command]` functions invoked from frontend via `invoke()`
- **Managed state**: `app.manage(AppState::new())` with `State<'_, AppState>` injection
- **Event system**: `app.emit()` for backend-to-frontend, `app.listen()` for frontend-to-backend
- **Plugin system**: Tauri plugins for reusable native functionality
- **Capability-based security** (v2): Declarative permission model in `capabilities/`
- **Multi-window**: Window management via `WebviewWindowBuilder`
- **Sidecar processes**: Bundled external binaries via `tauri::api::process::Command`
- **File system scope**: Restricted file access paths in configuration

## Common Anti-Patterns

- **Overly broad permissions**: `"allow-all"` capabilities instead of scoped permissions
- **Business logic in frontend**: Heavy computation or file I/O in JavaScript instead of Rust
- **Missing error handling**: Rust commands returning `Result` without proper error types for frontend
- **Synchronous IPC**: Blocking the main thread with synchronous command calls
- **Hardcoded paths**: Platform-specific paths instead of `app.path_resolver()`
- **Missing state management**: Using global mutable statics instead of `Mutex<AppState>`
- **Unbounded sidecar processes**: Spawning processes without cleanup/cancellation
- **Ignoring CSP**: Missing Content-Security-Policy in tauri configuration

## Performance Hotspots

- Large payloads over IPC bridge (serialize/deserialize overhead)
- Synchronous file operations blocking the Tauri async runtime
- Frontend bundle size affecting app startup time
- Missing lazy loading for large frontend routes
- Heavy Rust computation on the main thread (use `tokio::spawn` or `tauri::async_runtime`)
- Excessive IPC calls (batch operations instead of per-item calls)
- Large window creation overhead (reuse windows when possible)
- Missing image optimization for bundled assets

## Security Considerations

- **CSP configuration**: MUST set restrictive Content-Security-Policy in `tauri.conf.json`
- **Capability scoping** (v2): Minimize permissions per window/webview
- **File system scope**: Restrict accessible directories, never expose root
- **IPC input validation**: Validate all command parameters in Rust before processing
- **Updater security**: Signed updates with public key verification
- **Sidecar integrity**: Validate sidecar binary hashes
- **No remote content**: Avoid loading remote URLs in main window (phishing risk)
- **Shell command injection**: Sanitize inputs to `Command::new()` / sidecar args

## Testing Approach

- **Rust unit tests**: Standard `#[test]` for command logic and state management
- **Rust integration tests**: `tests/` directory for cross-module tests
- **Frontend unit/component**: Framework-specific tests (Vitest, Jest, Testing Library)
- **E2E**: `tauri-driver` with WebDriver protocol, or Playwright for web view testing
- **IPC contract tests**: Verify command signatures match frontend expectations
- **Coverage**: Rust via `cargo-tarpaulin`, frontend via Vitest/Jest

## Context7 Library IDs

- `tauri-apps/tauri` -- Tauri framework
- `tokio-rs/tokio` -- Async runtime (Tauri dependency)
- `serde-rs/serde` -- Serialization for IPC
- `tauri-apps/plugins-workspace` -- Official Tauri plugins
