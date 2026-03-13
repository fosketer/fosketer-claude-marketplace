# Go Language Profile

## Detection

- **Extensions**: `.go`
- **Project markers**: `go.mod`, `go.sum`, `go.work`
- **Version indicators**: `go` directive in `go.mod`

## Package Manifests

| File | Format | Notes |
|------|--------|-------|
| `go.mod` | `require` directives | Module-level dependency management |
| `go.sum` | Hash verification | Auto-generated, checked in |
| `go.work` | Workspace | Multi-module development |

## Common Patterns

- **Interface-based design**: Small interfaces (1-3 methods), accept interfaces return structs
- **Functional options**: `WithTimeout(5*time.Second)` for configurable constructors
- **Table-driven tests**: Slice of test cases with `t.Run()` subtests
- **Error wrapping**: `fmt.Errorf("context: %w", err)` for error chains
- **Context propagation**: `context.Context` as first parameter for cancellation/deadlines
- **Middleware pattern**: `func(http.Handler) http.Handler` for HTTP chains
- **Channel-based concurrency**: Goroutines communicating via channels
- **Struct embedding**: Composition over inheritance
- **Package-level organization**: One package per directory, package name = directory name
- **Init functions**: `func init()` for package initialization (use sparingly)

## Common Anti-Patterns

- **Empty interface abuse**: `interface{}` / `any` where typed interfaces are possible
- **Panic in libraries**: Using `panic()` instead of returning errors
- **Goroutine leaks**: Spawning goroutines without cancellation/cleanup
- **Ignoring errors**: `result, _ := function()` discarding error returns
- **God package**: Single `main` package with all logic
- **Pointer overuse**: `*string` for optional fields instead of zero values or wrapper types
- **Global mutable state**: Package-level `var` modified at runtime
- **Naked returns**: Named return values with bare `return` in long functions

## Complexity Indicators

- Functions >50 lines
- Files >500 lines
- Package with >20 exported symbols
- More than 3 levels of `if/else` nesting
- Functions with >5 parameters
- `select` statements with >5 cases
- Interface with >5 methods (split into smaller interfaces)

## Security Hotspots

- `os/exec.Command()` with user input -- command injection
- SQL string concatenation (use `database/sql` parameterized queries)
- `html/template` vs `text/template` confusion (XSS)
- Missing TLS configuration (`http.ListenAndServe` without TLS)
- Hardcoded secrets in source
- `unsafe` package usage -- memory safety bypassed
- Missing input validation on HTTP handlers
- `net/http` default client (no timeout -- SSRF, resource exhaustion)
- Race conditions (test with `-race` flag)
- Path traversal via `filepath.Join` with user input

## Performance Hotspots

- String concatenation in loops (use `strings.Builder`)
- Excessive allocations in hot paths (use `sync.Pool`)
- Missing buffered I/O (`bufio.Reader`/`bufio.Writer`)
- Unbuffered channels causing goroutine blocking
- JSON marshal/unmarshal in hot paths (consider code generation)
- Missing connection pooling for database/HTTP clients
- Large structs passed by value instead of pointer
- Defer in tight loops (slight overhead per iteration)
- Missing `context.WithTimeout` on external calls

## Testing Conventions

- **Frameworks**: Built-in `testing` package, `testify` for assertions
- **Structure**: `*_test.go` files co-located with source
- **Naming**: `TestFunctionName(t *testing.T)`, subtests via `t.Run("case", ...)`
- **Table-driven**: Standard pattern with `[]struct{ name string; ... }` test cases
- **Mocking**: `gomock`, `testify/mock`, interface-based test doubles
- **Integration**: Build tags `//go:build integration`
- **Coverage**: `go test -cover`, `go tool cover -html`
- **Benchmarks**: `BenchmarkFunctionName(b *testing.B)` with `b.N` loop
- **Race detection**: `go test -race`

## Context7 Library IDs

- `gin-gonic/gin` -- HTTP web framework
- `go-chi/chi` -- Lightweight HTTP router
- `jackc/pgx` -- PostgreSQL driver
- `uber-go/zap` -- Structured logging
- `stretchr/testify` -- Testing assertions
- `go-gorm/gorm` -- ORM
- `nats-io/nats.go` -- NATS messaging
