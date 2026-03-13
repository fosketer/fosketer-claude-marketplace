# C# Language Profile

## Detection

- **Extensions**: `.cs`, `.csx`, `.razor`
- **Project markers**: `*.csproj`, `*.sln`, `global.json`, `Directory.Build.props`, `Directory.Packages.props`
- **Version indicators**: `<TargetFramework>` in `.csproj`, `global.json` SDK version

## Package Manifests

| File | Format | Notes |
|------|--------|-------|
| `*.csproj` | `<PackageReference>` XML elements | Per-project |
| `Directory.Packages.props` | Central package management | Monorepo-wide version pinning |
| `packages.config` | XML | Legacy NuGet format |
| `nuget.config` | XML | Feed configuration |

## Common Patterns

- **Dependency injection**: Built-in `IServiceCollection`, constructor injection everywhere
- **Repository pattern**: `IRepository<T>` with EF Core implementations
- **CQRS + MediatR**: Command/query separation via MediatR pipeline
- **Vertical slice architecture**: Feature folders instead of layer folders
- **Options pattern**: `IOptions<T>` for typed configuration
- **Middleware pipeline**: ASP.NET Core request pipeline
- **Result pattern**: `Result<T>` instead of exceptions for expected failures
- **Extension methods**: Fluent APIs and service registration helpers
- **Records**: Immutable DTOs and value objects (C# 9+)
- **Minimal APIs**: Endpoint mapping without controllers (.NET 6+)

## Common Anti-Patterns

- **Service locator**: Resolving `IServiceProvider` directly instead of constructor injection
- **Anemic domain model**: Entities with only properties, no behavior
- **God controller**: Controllers with >10 action methods
- **Static helpers with state**: Static classes holding mutable state
- **Catching `Exception`**: `catch (Exception)` without filtering
- **String-based routing**: Magic strings for route names/paths
- **Synchronous over async**: `.Result` or `.Wait()` on async methods (deadlock risk)
- **Missing `ConfigureAwait`**: In library code (not needed in ASP.NET Core apps)

## Complexity Indicators

- Cyclomatic complexity >10 per method
- Classes with >20 methods or >500 lines
- Methods with >5 parameters
- Inheritance depth >3 levels
- Projects with >50 direct dependencies
- LINQ chains >5 operations without intermediate variables

## Security Hotspots

- SQL string concatenation (use parameterized queries or EF Core)
- `[AllowAnonymous]` on sensitive endpoints
- Missing `[Authorize]` attribute on controllers
- `HttpClient` without certificate validation
- Deserialization of untrusted data (`JsonSerializer.Deserialize` without type filtering)
- Hardcoded connection strings or secrets (use Azure Key Vault / user-secrets)
- Missing CORS policy or overly permissive `AllowAny`
- `Process.Start()` with user-controlled arguments
- Missing anti-forgery token validation on POST endpoints

## Performance Hotspots

- N+1 queries: `.Include()` missing in EF Core navigation properties
- `ToList()` on large queryables before filtering
- Synchronous database calls in async methods
- Missing response caching / output caching
- Large object allocations in hot paths (use `ArrayPool<T>`, `Span<T>`)
- String concatenation in loops (use `StringBuilder`)
- Missing `AsNoTracking()` for read-only EF Core queries
- Excessive middleware in pipeline

## Testing Conventions

- **Frameworks**: xUnit (preferred), NUnit, MSTest
- **Structure**: Separate `*.Tests` project per source project
- **Naming**: `ClassName_MethodName_ExpectedBehavior` or `Should_ExpectedBehavior_When_Condition`
- **Mocking**: Moq, NSubstitute, FakeItEasy
- **Integration**: `WebApplicationFactory<T>` for ASP.NET Core, Testcontainers
- **Coverage**: Coverlet, target >80% for domain/application layers
- **Architecture tests**: NetArchTest for enforcing layer boundaries

## Context7 Library IDs

- `dotnet/aspnetcore` -- ASP.NET Core framework
- `dotnet/efcore` -- Entity Framework Core
- `jbogard/MediatR` -- Mediator/CQRS
- `fluentvalidation/FluentValidation` -- Validation
- `serilog/serilog` -- Structured logging
- `App-vNext/Polly` -- Resilience/retry
- `dotnet/aspire` -- .NET Aspire orchestration
