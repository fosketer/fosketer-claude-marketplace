---
name: scan-security
description: |
  Detect hardcoded secrets, injection vectors, XSS, auth gaps, and OWASP top 10 vulnerabilities.
  Sub-skill of analyze-codebase — executed inline by the orchestrator.
---

# Scan Security

## Purpose

Analyze the codebase for security vulnerabilities aligned with the OWASP Top 10, including hardcoded secrets, injection vectors, XSS, authentication/authorization gaps, insecure deserialization, and sensitive data exposure.

The key words MUST, MUST NOT, SHOULD, SHOULD NOT, and MAY in this document are to be interpreted as described in RFC 2119.

## Input

- `PROJECT_PATH`: Root directory of the project being analyzed
- `STACK`: Detected language/framework (from Phase 1)
- `LANGUAGE_PROFILE`: Loaded language profile reference
- `FRAMEWORK_PROFILE`: Loaded framework profile reference (if applicable)
- `SCAN_REPORTS_DIR`: Path to `.code-analysis/scan-reports/` (for loading previous findings)
- `CHANGED_FILES`: Array of relative file paths changed since last scan, or null

## Workflow

### Step 1 — Scan for Hardcoded Secrets

1. Grep across all source files (excluding `node_modules`, `dist`, `bin`, `obj`, vendor directories) for secret patterns:
   - Assignment patterns: `API_KEY\s*=\s*["']`, `password\s*=\s*["']`, `secret\s*=\s*["']`, `token\s*=\s*["']`, `private_key\s*=\s*["']`
   - Connection strings: `(mongodb|postgres|mysql|redis|amqp)://\S+:\S+@`
   - Cloud credentials: `AKIA[0-9A-Z]{16}` (AWS), `sk-[a-zA-Z0-9]{20,}` (OpenAI), `-----BEGIN (RSA |EC )?PRIVATE KEY-----`
2. Exclude known safe patterns: environment variable reads (`os.environ`, `process.env`, `Environment.GetEnvironmentVariable`), placeholder values (`"changeme"`, `"xxx"`, `"<your-key>"`)
3. Severity: **critical** for all confirmed hardcoded secrets

### Step 2 — Check Injection Vectors

1. Grep for SQL/NoSQL injection risks:
   - String interpolation in queries: `f"SELECT .+ {`, `$"SELECT .+ {`, `` `SELECT .+ ${` ``, `"SELECT .+ " +`, `"SELECT .+ " \. format(`
   - Raw query execution with user input: `.raw(`, `.execute(`, `.query(` with concatenated or interpolated strings
   - NoSQL injection: unsanitized objects passed to `find(`, `aggregate(`, `$where`
2. Grep for command injection:
   - `os.system(`, `subprocess.call(` with `shell=True`, `` exec(` ``, `eval(`, `child_process.exec(`, `Process.Start(` with user-controlled input
3. Severity: **critical** for SQL injection with user input, **high** for command injection vectors

### Step 3 — Check Output Encoding (XSS)

1. Grep for XSS vectors:
   - **JavaScript/TypeScript**: `innerHTML`, `dangerouslySetInnerHTML`, `document.write(`, `outerHTML`
   - **Python (templates)**: `|safe`, `{% autoescape false %}`, `Markup(`, `mark_safe(`
   - **C# (Razor)**: `@Html.Raw(`, disabled output encoding
2. Check for user input flowing into these sinks without sanitization
3. Severity: **critical** for unsanitized user input in innerHTML/dangerouslySetInnerHTML, **high** for template-level autoescape bypass

### Step 4 — Check Authentication and Authorization

1. Grep for authentication middleware gaps:
   - **Express/Node**: route definitions without `auth`, `authenticate`, `isAuthenticated` middleware
   - **ASP.NET**: controllers/actions without `[Authorize]` attribute (compare against `[AllowAnonymous]` for intentional exceptions)
   - **Python (Django)**: views without `@login_required`, `@permission_required`, or `IsAuthenticated` permission class
   - **Python (FastAPI)**: endpoints without `Depends(` for auth dependency
2. Grep for CSRF protection gaps:
   - Missing CSRF token validation on `POST`/`PUT`/`DELETE` endpoints
   - `csrf_exempt`, `@csrf_exempt`, disabled CSRF middleware
3. Grep for authorization gaps:
   - State-changing endpoints without role/permission checks
   - Admin-only operations accessible without admin role verification
4. Severity: **critical** for missing auth on state-changing endpoints, **high** for missing CSRF protection

### Step 5 — Check Insecure Deserialization

1. Grep for dangerous deserialization patterns:
   - **Python**: `pickle.loads(`, `pickle.load(`, `yaml.load(` without `Loader=SafeLoader`, `marshal.loads(`
   - **JavaScript**: `JSON.parse(` of user input passed to `eval(` or `Function(`
   - **C#**: `BinaryFormatter.Deserialize(`, `XmlSerializer` with untrusted type, `JsonConvert.DeserializeObject` with `TypeNameHandling`
   - **Java**: `ObjectInputStream.readObject(`, `XMLDecoder`
2. Severity: **critical** for deserialization of untrusted input

### Step 6 — Check File Operations (Path Traversal)

1. Grep for user input in file path construction:
   - Path concatenation: `os.path.join(` with request parameters, `Path.Combine(` with user input, string concatenation with `/` or `\\` and user input
   - Missing sanitization: absence of `os.path.basename(`, `Path.GetFileName(`, or path traversal character stripping (`..`, `%2e%2e`)
2. Check for directory listing exposure: static file serving with directory browsing enabled
3. Severity: **critical** for path traversal with user input, **high** for directory listing exposure

### Step 7 — Check HTTP Requests (SSRF)

1. Grep for user-controlled URLs in outbound HTTP requests:
   - `requests.get(user_input`, `fetch(user_input`, `HttpClient` with user-provided URL
   - URL construction from user input without allowlist validation
2. Check for URL validation: presence of allowlists, blocklists, or URL parsing before requests
3. Severity: **high** for SSRF vectors without URL validation

### Step 8 — Check Logging for Sensitive Data

1. Grep for sensitive data in log statements:
   - `log.*(password`, `log.*(token`, `log.*(secret`, `log.*(credit_card`, `log.*(ssn`
   - `console.log(.*password`, `logger.info(.*token`
   - Request/response body logging without field filtering
2. Severity: **high** for passwords/tokens in logs, **medium** for PII in logs

### Step 9 — Check Security Headers

1. Grep for CORS configuration:
   - Overly permissive: `Access-Control-Allow-Origin: *`, `AllowAnyOrigin()`, `cors({ origin: '*' })`
   - Missing CORS configuration entirely on API endpoints
2. Check for Content Security Policy (CSP): Grep for `Content-Security-Policy` header configuration
3. Check for other security headers: `X-Content-Type-Options`, `X-Frame-Options`, `Strict-Transport-Security`
4. Severity: **high** for wildcard CORS on authenticated endpoints, **medium** for missing security headers

### Step 10 — Produce Findings

Compile findings array with each finding matching the Finding schema from `${CLAUDE_PLUGIN_ROOT}/references/output-schemas.md`:

```json
{
  "id": "SEC-e7b4a1-3f2a",
  "dimension": "security",
  "title": "Hardcoded API key in configuration",
  "description": "...",
  "severity": "critical",
  "file_path": "src/config/settings.py",
  "line_start": 15,
  "line_end": 15,
  "snippet": "API_KEY = \"sk-abc123...\"",
  "recommendation": "Move to environment variable or secret manager (Azure Key Vault, 1Password)",
  "effort": "low",
  "tags": ["hardcoded-secret", "owasp-a07"]
}
```

Always populate `snippet` with the relevant code lines when `line_start` is provided.

Return the findings array to the orchestrator.

## Error Handling

| Scenario | Resolution |
|----------|-----------|
| No web framework detected | Skip CSRF, CORS, and security header checks; focus on secrets and injection |
| Template engine not recognized | Skip XSS template checks, focus on DOM-based patterns |
| Very large codebase (>1000 files) | Prioritize request handlers and configuration files, note coverage limitation |
| Minified or bundled code detected | Skip those files, analyze source files only |
| False positive on secret pattern | Include finding but add `"confidence": "low"` note in description |

## Success Checklist

- [ ] Hardcoded secrets scanned across all source files
- [ ] SQL/NoSQL and command injection vectors checked
- [ ] XSS sinks identified and analyzed
- [ ] Authentication and authorization gaps detected
- [ ] CSRF protection verified on state-changing endpoints
- [ ] Insecure deserialization patterns flagged
- [ ] Path traversal vectors identified
- [ ] SSRF vectors checked
- [ ] Sensitive data in logs detected
- [ ] Security headers and CORS configuration reviewed
- [ ] All findings match the Finding schema
- [ ] Findings array returned to orchestrator

## Finding ID Generation

You MUST generate deterministic finding IDs using this algorithm.
NEVER use sequential numbering (001, 002) or free-form IDs.

### For findings with a file_path:

1. Compute file_hash6 (use python3 for cross-platform portability):
   ```bash
   python3 -c "import hashlib; print(hashlib.sha256(b'{relative_file_path}').hexdigest()[:6])"
   ```

2. Compute title_hash4 — normalize the finding title (lowercase, strip whitespace) and hash:
   ```bash
   python3 -c "import hashlib; print(hashlib.sha256(b'{normalized_lowercase_title}').hexdigest()[:4])"
   ```

3. ID = SEC-{file_hash6}-{title_hash4}

**Why title_hash instead of line_bucket:** Line numbers shift when code is refactored (e.g., 40-360 line shifts across iterations), breaking carry-forward ID matching and causing false "resolved" findings. Title hashes are stable across code movement — the same issue produces the same ID regardless of where in the file it appears.

### For findings without a file_path:

1. Compute title_hash4 (use python3 for cross-platform portability):
   ```bash
   python3 -c "import hashlib; print(hashlib.sha256(b'{normalized_lowercase_title}').hexdigest()[:4])"
   ```

2. ID = SEC-000000-{title_hash4}

### Collision resolution:

**Fresh scan** (no PREVIOUS_FINDINGS): sort by severity DESC then title ASC. First gets the bare ID, subsequent findings get -2, -3, etc.

**Carry-forward re-scan** (PREVIOUS_FINDINGS provided): carried-forward findings ALWAYS keep their existing ID, regardless of severity rank relative to new findings. When a new finding collides with a carried-forward ID:
1. Collect all existing IDs in this bucket (from carried-forward findings)
2. Find the highest existing suffix number (bare = 1, -2 = 2, -3 = 3, etc.)
3. Assign the new finding suffix = highest + 1
Example: if `SEC-8f3a21-a1b2` and `SEC-8f3a21-a1b2-2` are carried forward, a new collision gets `SEC-8f3a21-a1b2-3`.

## Carry-Forward Protocol

When PREVIOUS_FINDINGS is provided (not null), follow this two-phase scan.
When PREVIOUS_FINDINGS is null, skip this section and scan normally.

**Loading previous findings:** Read the latest scan report for this dimension from SCAN_REPORTS_DIR:
```
SCAN_REPORTS_DIR/*-security.json
```
Sort by filename date prefix, take most recent. Parse its `findings` array as PREVIOUS_FINDINGS. If no file found, PREVIOUS_FINDINGS = null.

### Phase 1 — Verify Previous Findings

For each finding in PREVIOUS_FINDINGS, in order:

A. If CHANGED_FILES is provided AND finding.file_path is NOT in CHANGED_FILES:
   → CARRY FORWARD unchanged. Copy the finding exactly (same ID, same severity,
     same description, same line numbers). Do NOT re-read the file.

B. If finding.file_path IS in CHANGED_FILES, OR if CHANGED_FILES is null:
   → Read the file at finding.file_path around finding.line_start to finding.line_end
   → Does the issue described in finding.description still exist?
     YES → carry forward with SAME ID. Update line numbers if code shifted.
           Since IDs use title_hash (not line numbers), the ID remains stable across line shifts.
     NO (resolved) → add to resolved_ids list. Do NOT include in output.
     FILE DELETED → add to resolved_ids list. Do NOT include in output.

### Cost Note on CHANGED_FILES=null

When CHANGED_FILES is null, Phase 1 re-reads every file referenced by previous findings,
and Phase 2 scans the full codebase. This can be MORE expensive than a fresh scan.
- ralph-loop SHOULD always provide CHANGED_FILES (via `git diff --name-only`)
- Initial `/analyze-codebase` scans pass CHANGED_FILES=null, which is acceptable because
  there are no PREVIOUS_FINDINGS on first scan
- If PREVIOUS_FINDINGS has >30 findings and CHANGED_FILES is null, the scanner MAY skip
  Phase 1 verification and carry all findings forward tentatively. In this case, set
  `unverified` in carry_forward_summary to the count of tentatively carried findings.
  Note: `unverified` is a **subset** of `carried_forward` (not additive).

### Phase 2 — Discover New Findings

1. Scan scope: CHANGED_FILES if provided, otherwise full codebase
2. For each new finding: verify no duplicate with carried-forward findings (same file and same or equivalent title). If duplicate, skip. If new, generate fingerprint ID.

### Output

DimensionReport MUST include:
1. All carried-forward findings (original IDs)
2. All new findings (new fingerprint IDs)
3. carry_forward_summary: { carried_forward, resolved, new, unverified, resolved_ids }

### Constraints

- NEVER re-describe a carried-forward finding in different words
- NEVER assign a new ID to a carried-forward unchanged finding
- NEVER carry forward without checking CHANGED_FILES first (if available)
