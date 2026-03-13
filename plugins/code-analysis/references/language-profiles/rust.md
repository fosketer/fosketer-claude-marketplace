# Rust Language Profile

## Detection

- **Extensions**: `.rs`
- **Project markers**: `Cargo.toml`, `Cargo.lock`, `rust-toolchain.toml`, `.cargo/config.toml`
- **Version indicators**: `edition` in `Cargo.toml` (2015, 2018, 2021, 2024), `rust-toolchain.toml`

## Package Manifests

| File | Format | Notes |
|------|--------|-------|
| `Cargo.toml` | `[dependencies]`, `[dev-dependencies]`, `[build-dependencies]` | Per-crate manifest |
| `Cargo.lock` | Lock file | Checked in for binaries, not for libraries |
| Workspace `Cargo.toml` | `[workspace.members]` | Monorepo management |

## Common Patterns

- **Trait-based polymorphism**: Traits instead of inheritance, `impl Trait` for generics
- **Builder pattern**: `StructBuilder::new().field(val).build()` for complex construction
- **Newtype pattern**: `struct UserId(u64)` for type safety
- **Error handling**: `Result<T, E>` with `thiserror`/`anyhow`, `?` operator propagation
- **Iterator chains**: Functional-style `.iter().map().filter().collect()`
- **RAII**: Drop trait for resource cleanup
- **Type state pattern**: Compile-time state machine enforcement
- **Module system**: `mod.rs` or `module/mod.rs` for submodule organization
- **Derive macros**: `#[derive(Debug, Clone, Serialize)]` for trait implementation

## Common Anti-Patterns

- **Excessive `.clone()`**: Cloning to avoid borrow checker instead of proper lifetimes
- **Unwrap in production**: `.unwrap()` / `.expect()` in non-test code
- **String everywhere**: Using `String` where `&str`, enums, or newtypes are appropriate
- **Mutex<Vec<T>> for concurrent collections**: Using `DashMap` or channels instead
- **God module**: Single `lib.rs` or `main.rs` with >500 lines
- **Ignoring `clippy` warnings**: Suppressing lints without justification
- **`unsafe` without documentation**: Using unsafe blocks without safety comments
- **Arc<Mutex<T>> overuse**: When message passing or `RwLock` would be more appropriate

## Complexity Indicators

- Functions >50 lines
- Generic type parameters >3 per function/struct
- Lifetime annotations >2 per function signature
- Trait bounds >3 where clauses
- Nested `match` statements >3 levels
- Files with >400 lines
- Crate dependency count >50

## Security Hotspots

- `unsafe` blocks -- memory safety bypassed
- FFI boundaries (`extern "C"`) -- manual memory management
- Deserialization of untrusted data (`serde` without validation)
- `std::process::Command` with user input -- command injection
- Path traversal via user-supplied file paths
- Integer overflow (debug panics, release wraps silently)
- Missing TLS certificate validation in HTTP clients
- Race conditions in `unsafe` concurrent code

## Performance Hotspots

- Excessive heap allocations (`Box`, `Vec`, `String` in hot paths)
- Missing `#[inline]` on small frequently-called functions across crate boundaries
- `collect()` into `Vec` when iterator would suffice
- Lock contention with `Mutex` in concurrent code
- Missing `with_capacity()` for known-size collections
- Synchronous I/O in async runtime (blocking the executor)
- Large enum variants causing wasted stack space (box large variants)
- Missing `release` profile optimizations (`lto`, `codegen-units = 1`)

## Testing Conventions

- **Frameworks**: Built-in `#[test]`, `#[cfg(test)]` modules
- **Structure**: Unit tests in `mod tests` at bottom of source file, integration tests in `tests/`
- **Naming**: `test_<behavior>` or `should_<behavior>_when_<condition>`
- **Mocking**: `mockall`, `wiremock` for HTTP
- **Property testing**: `proptest`, `quickcheck`
- **Coverage**: `cargo-tarpaulin`, `cargo-llvm-cov`
- **Benchmarks**: `criterion` crate, `#[bench]` (nightly)

## Context7 Library IDs

- `tokio-rs/tokio` -- Async runtime
- `serde-rs/serde` -- Serialization framework
- `hyperium/hyper` -- HTTP library
- `actix/actix-web` -- Web framework
- `tauri-apps/tauri` -- Desktop app framework
- `diesel-rs/diesel` -- ORM
- `launchbadge/sqlx` -- Async SQL toolkit
