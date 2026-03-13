# Flutter Framework Profile

## Detection Markers

- `pubspec.yaml` with `flutter` SDK dependency
- `lib/main.dart` with `runApp()` call
- `android/`, `ios/`, `web/`, `macos/`, `linux/`, `windows/` platform directories
- `analysis_options.yaml` with `flutter_lints` or `very_good_analysis`
- `.metadata` file with Flutter version info

## Architecture Expectations

```
lib/
  main.dart                # App entry point
  app.dart                 # MaterialApp / root widget
  core/                    # Shared utilities, theme, constants
    theme/
    constants/
    utils/
  features/                # Feature-first organization
    feature_name/
      data/                # Repositories, data sources, models
      domain/              # Entities, use cases, repository interfaces
      presentation/        # Widgets, BLoC/cubit, pages
  l10n/                    # Localization
  routing/                 # Route definitions (go_router)
test/
  features/                # Mirrors lib/ structure
  widget_test/             # Widget tests
  integration_test/        # Integration/E2E tests
```

- Feature-first organization SHOULD be preferred over layer-first
- Business logic MUST NOT live in widgets
- State management SHOULD be consistent across features (BLoC, Riverpod, or Provider)

## Common Patterns

- **BLoC/Cubit**: Event-driven state management with `Bloc<Event, State>` or `Cubit<State>`
- **Riverpod**: Provider-based state management with code generation
- **Repository pattern**: Abstract data source behind repository interfaces
- **Freezed models**: Code-generated immutable data classes with union types
- **GoRouter**: Declarative routing with type-safe parameters
- **Dependency injection**: `get_it` service locator or Riverpod providers
- **Theming**: `ThemeData` + `ThemeExtension` for consistent design tokens
- **Platform channels**: `MethodChannel` for native platform communication

## Common Anti-Patterns

- **setState for complex state**: Using `setState` beyond simple local UI state
- **Build method bloat**: Single `build()` method >100 lines without widget extraction
- **Deep nesting**: >8 levels of widget nesting (extract sub-widgets)
- **Missing const constructors**: Preventing rebuild optimization
- **Logic in widgets**: Business logic mixed into widget `build()` methods
- **Hardcoded strings**: UI text not in localization files
- **StatefulWidget overuse**: Using `StatefulWidget` where `StatelessWidget` + state management works
- **Untyped routes**: String-based routing instead of `go_router` typed routes
- **Missing error states**: BLoC/Cubit without error/loading states

## Performance Hotspots

- Missing `const` constructors on frequently rebuilt widgets
- Large widget trees rebuilt on every state change (split into smaller widgets)
- Missing `ListView.builder` for scrollable lists (eager `Column` with many children)
- Heavy image assets without caching (`cached_network_image`)
- Missing `RepaintBoundary` around animation-heavy subtrees
- Expensive operations in `build()` (move to `initState` or async init)
- Platform channel calls on main isolate for heavy computation
- Missing pagination for API list calls

## Security Considerations

- Hardcoded API keys in Dart source (extractable from APK/IPA)
- Sensitive data in `SharedPreferences` (use `flutter_secure_storage`)
- Missing certificate pinning for production API calls
- WebView with unrestricted JavaScript execution
- Missing obfuscation (`--obfuscate --split-debug-info` for release builds)
- Logging sensitive user data
- Deep link handling without validation

## Testing Approach

- **Unit**: `test` package for business logic, BLoC/Cubit, repositories
- **Widget**: `flutter_test` with `pumpWidget()`, `find.*`, `expect()`
- **Integration**: `integration_test` package for full app flows
- **BLoC testing**: `bloc_test` with `blocTest()` for state transitions
- **Mocking**: `mocktail` (preferred) or `mockito`
- **Golden tests**: Screenshot comparison for UI regression
- **Coverage**: `flutter test --coverage`, target >80% for domain/data

## Context7 Library IDs

- `flutter/flutter` -- Flutter framework
- `felangel/bloc` -- BLoC state management
- `rrousselGit/riverpod` -- Riverpod state management
- `fluttercommunity/plus_plugins` -- Community plugins
- `dart-lang/sdk` -- Dart SDK
