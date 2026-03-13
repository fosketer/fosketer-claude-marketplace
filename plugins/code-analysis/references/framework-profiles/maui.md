# .NET MAUI Framework Profile

## Detection Markers

- `*.csproj` with `<UseMaui>true</UseMaui>` or SDK `Microsoft.NET.Sdk.Maui`
- `MauiProgram.cs` with `MauiApp.CreateBuilder()`
- `Platforms/` directory with `Android/`, `iOS/`, `MacCatalyst/`, `Windows/` subdirectories
- `App.xaml` / `App.xaml.cs` application entry point
- `*.xaml` files with `xmlns="http://schemas.microsoft.com/dotnet/2021/maui"`

## Architecture Expectations

```
Project/
  App.xaml(.cs)            # Application entry, resource dictionaries
  MauiProgram.cs           # DI registration, service configuration
  AppShell.xaml(.cs)       # Shell navigation structure
  Models/                  # Data models, DTOs
  ViewModels/              # MVVM view models (ObservableObject)
  Views/ | Pages/          # XAML pages and content views
  Services/                # Business logic, API clients, platform services
  Converters/              # IValueConverter implementations
  Controls/                # Custom controls and templates
  Resources/
    Styles/                # Global styles, colors, fonts
    Images/                # SVG/PNG assets
    Fonts/                 # Custom fonts
    Raw/                   # Raw assets
  Platforms/
    Android/               # Android-specific code (MainActivity, AndroidManifest)
    iOS/                   # iOS-specific code (AppDelegate, Info.plist)
    MacCatalyst/           # Mac-specific code
    Windows/               # Windows-specific code
```

- MVVM pattern MUST be followed (CommunityToolkit.Mvvm preferred)
- Views MUST NOT contain business logic (code-behind should be minimal)
- Platform-specific code SHOULD use `#if` directives or partial classes

## Common Patterns

- **MVVM with CommunityToolkit**: `[ObservableProperty]`, `[RelayCommand]` source generators
- **Shell navigation**: `Shell.Current.GoToAsync("//route")` for URI-based navigation
- **Dependency injection**: Built-in `IServiceCollection` in `MauiProgram.cs`
- **MessagingCenter / WeakReferenceMessenger**: Decoupled view-to-viewmodel communication
- **Data binding**: XAML `{Binding Property}` with `INotifyPropertyChanged`
- **Handlers / Custom renderers**: Platform-specific UI customization
- **Behaviors**: Attached behaviors for reusable UI logic
- **Platform services**: `#if ANDROID` / `#if IOS` conditional compilation

## Common Anti-Patterns

- **Code-behind logic**: Business logic in `.xaml.cs` instead of ViewModels
- **Tight coupling to Shell**: Navigation logic spread across views instead of centralized
- **Missing async commands**: Synchronous commands blocking the UI thread
- **XAML god pages**: Single page with >300 lines of XAML (extract controls)
- **Hardcoded colors/sizes**: Inline values instead of resource dictionary references
- **ViewModel coupling**: ViewModels referencing Views or other ViewModels directly
- **Missing error handling**: No try-catch in async command handlers (silent failures)
- **Platform spaghetti**: Excessive `#if` directives instead of platform service abstraction

## Performance Hotspots

- **CollectionView**: Missing `ItemSizingStrategy="MeasureFirstItem"` for uniform items
- **Large XAML trees**: Deeply nested layouts without virtualization
- **Image loading**: Missing caching, loading full-resolution images for thumbnails
- **Startup time**: Too many services registered eagerly in DI (use lazy/transient)
- **Layout passes**: Excessive nested `Grid`/`StackLayout` causing multiple measure passes
- **Missing compiled bindings**: `x:DataType` not set, falling back to reflection binding
- **Animation overhead**: Complex animations on low-end mobile devices
- **Missing `CancellationToken`**: Long-running operations without cancellation support

## Security Considerations

- Sensitive data in `SecureStorage` (not `Preferences`)
- API keys in source code (extractable from app packages)
- Missing certificate pinning for production API calls
- Insecure `HttpClient` configuration (missing TLS enforcement)
- Missing obfuscation for release builds
- Deep link handling without input validation
- Platform permissions requested too broadly (minimum necessary)
- Missing `ProGuard`/`R8` rules for Android (code stripping)

## Testing Approach

- **Unit**: xUnit + Moq for ViewModels, Services, and Models
- **ViewModel**: Test command execution, property changes, navigation calls
- **UI**: `Microsoft.Maui.Controls.Testing` (limited), or Appium for device testing
- **Integration**: Test service layer with real/mocked HTTP (Testcontainers)
- **Platform**: Device farm testing (App Center, BrowserStack) for platform-specific issues
- **Coverage**: Coverlet, target >80% for ViewModels/Services, lower for platform code

## Context7 Library IDs

- `dotnet/maui` -- .NET MAUI framework
- `CommunityToolkit/Maui` -- MAUI Community Toolkit
- `CommunityToolkit/dotnet` -- MVVM Toolkit (ObservableObject, RelayCommand)
- `jamesmontemagno/mvvm-helpers` -- MVVM helpers
- `reactiveui/ReactiveUI` -- Reactive MVVM (alternative)
