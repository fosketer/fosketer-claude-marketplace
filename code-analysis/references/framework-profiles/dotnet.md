# .NET Framework Profile

## Detection Markers

- `*.sln` solution file
- `*.csproj` with `<Project Sdk="Microsoft.NET.Sdk.Web">` or `Microsoft.NET.Sdk`
- `Program.cs` with `WebApplication.CreateBuilder()` or `Host.CreateDefaultBuilder()`
- `appsettings.json`, `appsettings.*.json`
- `.NET Aspire`: `*.AppHost.csproj` with `Aspire.Hosting` reference

## Architecture Expectations

```
Solution.sln
  src/
    Project.Api/          # HTTP endpoints (controllers or minimal APIs)
    Project.Application/  # Use cases, commands, queries (MediatR)
    Project.Domain/       # Entities, value objects, domain services
    Project.Infrastructure/ # EF Core, external services, repositories
  tests/
    Project.Api.Tests/
    Project.Application.Tests/
    Project.Domain.Tests/
    Project.Infrastructure.Tests/
```

- Dependency flow: Api -> Application -> Domain; Infrastructure -> Application
- Domain MUST NOT reference Infrastructure or Api
- Vertical slice alternative: feature folders with all layers co-located

## Common Patterns

- **Minimal APIs**: `app.MapGet("/api/items", handler)` for lightweight endpoints
- **MediatR CQRS**: Separate command/query handlers with pipeline behaviors
- **Repository + Unit of Work**: EF Core DbContext as UoW, repository abstraction
- **Options pattern**: `IOptions<T>` / `IOptionsSnapshot<T>` for typed configuration
- **Health checks**: `app.MapHealthChecks("/health")` with custom checks
- **Background services**: `IHostedService` / `BackgroundService` for background work
- **Result pattern**: `Result<T>` for expected failures instead of exceptions
- **Middleware pipeline**: Request/response pipeline with `app.Use*()` methods
- **Aspire orchestration**: `AddProject`, `AddPostgres`, `WithReference` for service composition

## Common Anti-Patterns

- **Controller bloat**: Controllers with >5 actions or >200 lines
- **Anemic domain model**: Entities with only getters/setters, no behavior
- **Service locator**: Injecting `IServiceProvider` and resolving at runtime
- **Sync over async**: `.Result`, `.Wait()`, `.GetAwaiter().GetResult()` -- deadlock risk
- **Missing validation**: No FluentValidation or DataAnnotations on request DTOs
- **DbContext lifetime**: Singleton `DbContext` in DI (MUST be scoped)
- **Exception-driven flow**: Using exceptions for expected business cases
- **Hardcoded connection strings**: In `Program.cs` instead of configuration

## Performance Hotspots

- N+1 queries: missing `.Include()` / `.ThenInclude()` in EF Core
- `ToList()` on large queryables before server-side filtering
- Missing `AsNoTracking()` for read-only queries
- Missing response caching or output caching middleware
- Synchronous I/O in async request pipeline
- Large object heap pressure (reuse buffers with `ArrayPool<T>`)
- Missing pagination on list endpoints
- EF Core change tracking overhead on bulk operations

## Security Considerations

- Missing `[Authorize]` on protected endpoints
- Overly permissive CORS (`AllowAny` origins with credentials)
- Missing anti-forgery tokens on mutation endpoints
- SQL injection via raw SQL (`FromSqlRaw` with string interpolation)
- Mass assignment (binding directly to entity instead of DTO)
- Missing rate limiting on public APIs
- Secrets in `appsettings.json` (use user-secrets or Key Vault)
- Missing HTTPS redirection middleware

## Testing Approach

- **Unit**: xUnit + Moq/NSubstitute for domain and application layers
- **Integration**: `WebApplicationFactory<T>` for API tests with real middleware pipeline
- **Database**: Testcontainers for PostgreSQL/SQL Server, or in-memory provider for simple cases
- **Architecture**: NetArchTest for enforcing dependency rules
- **Coverage**: Coverlet, target >80% for domain/application, >60% for API
- **Load**: NBomber or k6 for performance testing

## Context7 Library IDs

- `dotnet/aspnetcore` -- ASP.NET Core
- `dotnet/efcore` -- Entity Framework Core
- `jbogard/MediatR` -- Mediator/CQRS
- `fluentvalidation/FluentValidation` -- Validation
- `serilog/serilog` -- Structured logging
- `App-vNext/Polly` -- Resilience policies
- `dotnet/aspire` -- .NET Aspire
- `DapperLib/Dapper` -- Micro ORM
