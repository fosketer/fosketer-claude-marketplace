# TypeScript Language Profile

## Detection

- **Extensions**: `.ts`, `.tsx`, `.mts`, `.cts`
- **Project markers**: `tsconfig.json`, `tsconfig.*.json`, `package.json` with `typescript` dependency
- **Version indicators**: `typescript` version in `package.json`

## Package Manifests

| File | Format | Notes |
|------|--------|-------|
| `package.json` | `dependencies`, `devDependencies` | npm/yarn/pnpm |
| `pnpm-lock.yaml` | Lock file | pnpm workspace indicator |
| `yarn.lock` | Lock file | Yarn indicator |
| `package-lock.json` | Lock file | npm indicator |
| `bun.lockb` | Binary lock | Bun indicator |

## Common Patterns

- **Barrel exports**: `index.ts` re-exporting from a directory
- **Dependency injection**: Constructor injection, InversifyJS, tsyringe, NestJS providers
- **Repository pattern**: Data access abstraction with interfaces
- **Factory pattern**: Generic factory functions, builder pattern with method chaining
- **Strategy pattern**: Interfaces + implementations, discriminated unions
- **Discriminated unions**: `type Result = Success | Failure` with `kind` discriminator
- **Generics**: Utility types, generic repositories, typed hooks
- **Zod/io-ts validation**: Runtime type validation at boundaries
- **Module augmentation**: Declaration merging for library extensions

## Common Anti-Patterns

- **`any` type usage**: Defeats type safety, especially in function signatures
- **Type assertions abuse**: `as unknown as T` to bypass type checking
- **Enum overuse**: String literal unions are often simpler
- **Barrel file bloat**: Re-exporting everything causes tree-shaking issues
- **Implicit `any`**: Missing `strict: true` in tsconfig
- **Callback hell**: Nested `.then()` chains instead of async/await
- **Non-null assertions abuse**: `value!.property` without validation
- **Circular dependencies**: Especially in barrel files and shared types

## Complexity Indicators

- Cyclomatic complexity >10 per function
- Generic type nesting >3 levels deep
- Files with >300 lines
- Functions with >5 parameters
- More than 3 conditional type levels
- Union types with >8 members without discriminator

## Security Hotspots

- `eval()`, `new Function()` -- code injection
- `innerHTML`, `dangerouslySetInnerHTML` -- XSS
- Template literal SQL queries (use parameterized queries)
- `JSON.parse()` on untrusted input without validation
- Missing CORS configuration
- Hardcoded API keys, tokens, secrets
- `child_process.exec()` with user input -- command injection
- `fs.readFile()` with user-controlled paths -- path traversal
- Missing `httpOnly`/`secure` flags on cookies

## Performance Hotspots

- Bundle size: importing entire libraries (`import _ from 'lodash'` vs `import map from 'lodash/map'`)
- Re-renders: missing `React.memo`, unstable object/function references in props
- Missing pagination on API list endpoints
- Synchronous `fs` operations in server hot paths
- N+1 queries in ORM loops (Prisma, TypeORM, Sequelize)
- Large `node_modules` in serverless deployments
- Missing tree-shaking (CommonJS instead of ESM)

## Testing Conventions

- **Frameworks**: Jest, Vitest, Mocha, Playwright, Cypress
- **Structure**: `__tests__/` directories or `*.test.ts` / `*.spec.ts` co-located
- **Naming**: `describe('ClassName')` > `it('should do X')`
- **Mocking**: `jest.mock()`, `vi.mock()`, manual mocks in `__mocks__/`
- **Coverage**: Istanbul/c8, target >80% for business logic
- **E2E**: Playwright or Cypress for frontend, Supertest for API

## Context7 Library IDs

- `microsoft/TypeScript` -- TypeScript compiler
- `expressjs/express` -- Express web framework
- `nestjs/nest` -- NestJS framework
- `prisma/prisma` -- Prisma ORM
- `colinhacks/zod` -- Schema validation
- `TanStack/query` -- Data fetching/caching
- `vercel/next.js` -- Next.js framework
