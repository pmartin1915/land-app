# Code Review Checklist

Use this checklist systematically when reviewing code changes.

## 1. Logic & Correctness

- [ ] Off-by-one errors in loops, slices, array indexes
- [ ] Null/undefined handling - what if the value is missing?
- [ ] Type coercion bugs (`==` vs `===`, `parseInt` without radix)
- [ ] Async/await - are ALL promises handled? No floating promises?
- [ ] Race conditions in state updates (stale closures, concurrent mutations)
- [ ] Edge cases: empty arrays, zero values, negative numbers, MAX_INT
- [ ] Boolean logic errors (De Morgan's law violations, short-circuit issues)
- [ ] String handling: empty strings, whitespace-only, unicode edge cases

## 2. Security

- [ ] User input sanitization before use
- [ ] SQL/NoSQL injection vectors
- [ ] XSS in rendered content (especially with dangerouslySetInnerHTML)
- [ ] Secrets in code, logs, or error messages
- [ ] CORS/CSRF protections on API endpoints
- [ ] Authentication checks before sensitive operations
- [ ] Authorization - does the user have permission for THIS resource?
- [ ] Path traversal in file operations
- [ ] Command injection in shell commands
- [ ] Sensitive data in URLs (appears in logs, browser history)

## 3. Error Handling

- [ ] Try/catch in async code (promises without .catch are silent failures)
- [ ] User-facing error messages (no stack traces, no internal details)
- [ ] Retry logic for transient failures (network, rate limits)
- [ ] Graceful degradation when dependencies fail
- [ ] Logging for debugging (but not sensitive data)
- [ ] Error boundaries in React components
- [ ] Timeout handling for external calls

## 4. Performance

- [ ] N+1 queries (loops that trigger DB/API calls)
- [ ] Unbounded loops or recursion
- [ ] Memory leaks (event listeners not removed, subscriptions not cleaned)
- [ ] Bundle size impact of new dependencies
- [ ] Unnecessary re-renders in React (check dependency arrays)
- [ ] Large objects in state/context causing prop drilling re-renders
- [ ] Missing pagination on lists
- [ ] Missing debounce/throttle on frequent events

## 5. Maintainability

- [ ] Function length - over 50 lines is a smell
- [ ] File length - over 500 lines should be split
- [ ] Cyclomatic complexity - too many if/else branches
- [ ] Magic numbers and strings - should be named constants
- [ ] Dead code - commented out code, unused imports/variables
- [ ] Consistent naming - follows project conventions
- [ ] Single responsibility - one function/component does one thing
- [ ] DRY violations - same logic repeated in multiple places

## 6. Testing

- [ ] New code has corresponding tests
- [ ] Edge cases are covered (not just happy path)
- [ ] Mocks are realistic (don't hide real bugs)
- [ ] Tests are deterministic (no `Math.random()`, no race conditions)
- [ ] Test descriptions are clear about what they verify
- [ ] Integration tests for critical paths
- [ ] No `any` types used to bypass TypeScript in tests

## 7. React/Frontend Specific

- [ ] useEffect dependency arrays are complete (ESLint exhaustive-deps)
- [ ] No state updates during render (infinite loops)
- [ ] Keys on list items (not array index for dynamic lists)
- [ ] Accessibility: aria-labels, keyboard navigation, focus management
- [ ] Responsive design considered
- [ ] Loading states for async operations
- [ ] Error states shown to users
- [ ] Form validation and error messages
- [ ] Cleanup in useEffect return (subscriptions, timers)

## 8. API/Backend Specific

- [ ] Input validation at API boundaries
- [ ] Rate limiting on public endpoints
- [ ] Pagination for list endpoints
- [ ] Idempotency for mutation endpoints
- [ ] Database indexes for query patterns
- [ ] Transaction handling for multi-step operations
- [ ] Consistent error response format
- [ ] API versioning considered

## 9. State Management

- [ ] Optimistic updates have rollback on failure
- [ ] Loading states while mutations are in flight
- [ ] Stale data detection after mutations
- [ ] Concurrent mutation handling (what if user clicks twice?)
- [ ] URL state synced with application state
- [ ] Persistent state survives refresh when appropriate

## 10. Git Hygiene

- [ ] Commit messages are descriptive
- [ ] No unrelated changes bundled
- [ ] No commented-out code committed
- [ ] No console.log debugging left behind
- [ ] No TODO comments without issue references
- [ ] Secrets not in commit history
- [ ] Large files not committed (should be in .gitignore)

## Quick Severity Guide

| If you find this... | Severity |
|---------------------|----------|
| Security vulnerability | CRITICAL |
| Data loss possible | CRITICAL |
| App crashes in normal use | CRITICAL |
| Logic bug in core flow | HIGH |
| Race condition | HIGH |
| Missing error handling | HIGH |
| No tests for new code | MEDIUM |
| Performance concern | MEDIUM |
| Code smell | MEDIUM |
| Style inconsistency | LOW |
| Missing docs | LOW |
