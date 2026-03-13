# React Framework Profile

## Detection Markers

- `package.json` with `react` and `react-dom` dependencies
- `.tsx` / `.jsx` files with JSX syntax
- `next.config.*` (Next.js), `vite.config.*` (Vite), `remix.config.*` (Remix)
- Presence of `src/App.tsx` or `src/main.tsx` or `pages/` / `app/` directories

## Architecture Expectations

```
src/
  components/       # Reusable UI components
  pages/ | routes/  # Page-level components / route handlers
  hooks/            # Custom React hooks
  contexts/         # React context providers
  stores/           # State management (Zustand, Redux)
  services/ | api/  # API client functions
  utils/ | lib/     # Pure utility functions
  types/            # Shared TypeScript types
  assets/           # Static assets (images, fonts)
```

- Components SHOULD follow single-responsibility principle
- Business logic SHOULD live in hooks/services, not in components
- State management SHOULD be centralized (Zustand, Redux, Jotai) for shared state

## Common Patterns

- **Custom hooks**: `useXxx()` for reusable stateful logic
- **Container/Presentational split**: Logic hooks + pure render components
- **Compound components**: `<Select>` + `<Select.Option>` pattern
- **Render props / children as function**: For flexible component composition
- **Error boundaries**: `ErrorBoundary` wrapping critical subtrees
- **Suspense + lazy loading**: `React.lazy()` for code splitting
- **Controlled components**: Form state managed by React, not DOM
- **Memoization**: `React.memo`, `useMemo`, `useCallback` for performance

## Common Anti-Patterns

- **Prop drilling**: Passing props through >3 component levels (use context or state manager)
- **useEffect for derived state**: Computing values in effects instead of `useMemo`
- **Unstable references**: Inline objects/functions in JSX causing unnecessary re-renders
- **Missing dependency arrays**: `useEffect`/`useMemo`/`useCallback` without deps
- **State in URL not synced**: Form/filter state not reflected in URL params
- **Direct DOM manipulation**: `document.querySelector` instead of refs
- **Index as key**: Using array index as `key` for dynamic lists
- **Business logic in components**: API calls and transforms directly in render components

## Performance Hotspots

- Unnecessary re-renders: check with React DevTools Profiler
- Large bundle size: missing code splitting, importing entire libraries
- Missing `React.memo` on expensive pure components
- Inline object/function creation in JSX props
- Missing virtualization for long lists (use `react-window` / `react-virtuoso`)
- Heavy computations in render path (move to `useMemo` or web workers)
- Unoptimized images (missing lazy loading, wrong format)
- Missing Suspense boundaries for async data

## Security Considerations

- `dangerouslySetInnerHTML` -- XSS risk, audit all usages
- User input rendered without sanitization
- Storing tokens in `localStorage` (prefer `httpOnly` cookies)
- Missing CSP headers for script injection protection
- Third-party script injection via unvetted dependencies
- Sensitive data in client-side state (visible in DevTools)
- CORS misconfigurations allowing credential leakage

## Testing Approach

- **Unit**: React Testing Library for component behavior, Vitest/Jest for hooks and utils
- **Integration**: Testing Library with MSW for API mocking
- **E2E**: Playwright or Cypress
- **Visual regression**: Storybook + Chromatic or Percy
- **Coverage targets**: >80% for hooks/utils, >60% for components
- Focus on user behavior (`getByRole`, `getByText`) not implementation details

## Context7 Library IDs

- `facebook/react` -- React core
- `vercel/next.js` -- Next.js framework
- `TanStack/query` -- Data fetching (React Query)
- `pmndrs/zustand` -- State management
- `mantine-dev/mantine` -- Component library
- `mui/material-ui` -- MUI component library
- `testing-library/react-testing-library` -- Testing utilities
- `mswjs/msw` -- API mocking for tests
