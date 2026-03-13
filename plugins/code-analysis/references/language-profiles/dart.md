# Dart Language Profile

## Detection

- **Extensions**: `.dart`
- **Project markers**: `pubspec.yaml`, `analysis_options.yaml`, `.dart_tool/`
- **Version indicators**: `environment.sdk` in `pubspec.yaml`, `dart` version constraint

## Package Manifests

| File | Format | Notes |
|------|--------|-------|
| `pubspec.yaml` | `dependencies`, `dev_dependencies` | Primary manifest |
| `pubspec.lock` | Lock file | Auto-generated |

## Common Patterns

- **BLoC pattern**: Business Logic Component with streams/cubits
- **Provider pattern**: `ChangeNotifier` + `Provider` for state management
- **Riverpod**: Type-safe provider with code generation
- **Repository pattern**: Abstract repository interfaces with implementations
- **Freezed models**: Immutable data classes with union types via code generation
- **Extension methods**: Adding functionality to existing types
- **Mixins**: Code reuse without inheritance hierarchy
- **Factory constructors**: Named constructors for complex initialization
- **Null safety**: Sound null safety with `?`, `!`, `late` keywords
- **Isolates**: For CPU-intensive work off the main thread

## Common Anti-Patterns

- **setState overuse**: Managing complex state with `setState` instead of state management
- **Build method bloat**: Widget `build()` methods >100 lines
- **Deep widget nesting**: >10 levels of widget nesting without extraction
- **Ignoring null safety**: Excessive `!` operator usage
- **String-based navigation**: Route strings instead of typed routes (go_router)
- **God widget**: Single widget managing too many concerns
- **Missing `const` constructors**: Preventing widget rebuild optimization
- **Implicit `dynamic`**: Missing type annotations causing runtime errors

## Complexity Indicators

- Widget `build()` methods >50 lines
- Classes with >15 methods
- Files with >300 lines
- Functions with >5 parameters
- Nested `FutureBuilder`/`StreamBuilder` >2 levels
- More than 3 levels of callback nesting

## Security Hotspots

- Hardcoded API keys in source (especially in mobile apps)
- HTTP instead of HTTPS for API calls
- Insecure storage (`SharedPreferences` for sensitive data -- use `flutter_secure_storage`)
- Missing certificate pinning for production apps
- `dart:mirrors` usage in production (reflection, code injection)
- WebView `javaScriptMode: JavaScriptMode.unrestricted` without sanitization
- Logging sensitive user data

## Performance Hotspots

- Rebuilding entire widget trees (missing `const`, missing selective rebuilds)
- Large images without caching or resizing
- Synchronous file I/O on main isolate
- Missing `ListView.builder` for large lists (using `ListView` with `children`)
- Expensive computations in `build()` method
- Missing `RepaintBoundary` for complex animations
- Unbounded list fetching without pagination

## Testing Conventions

- **Frameworks**: `test` (unit), `flutter_test` (widget), `integration_test` (integration)
- **Structure**: `test/` directory mirroring `lib/` layout
- **Naming**: `<module>_test.dart`, groups with `group()`, tests with `test()`/`testWidgets()`
- **Mocking**: `mocktail` or `mockito` with `@GenerateMocks`
- **Widget testing**: `pumpWidget()`, `find.byType()`, `expect(find.text())`
- **Coverage**: `flutter test --coverage`, target >80%
- **Golden tests**: Screenshot comparison for UI regression

## Context7 Library IDs

- `flutter/flutter` -- Flutter framework
- `rrousselGit/riverpod` -- Riverpod state management
- `felangel/bloc` -- BLoC pattern
- `dart-lang/sdk` -- Dart SDK
- `fluttercommunity/plus_plugins` -- Flutter community plugins
