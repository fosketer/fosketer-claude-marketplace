---
name: scan-security
version: 0.8.0
description: |
  This skill should be used when the user asks to "find hardcoded secrets", "check for injection vulnerabilities",
  "scan for XSS", "OWASP top 10 audit", or when detecting hardcoded secrets, injection vectors, XSS, auth gaps,
  and OWASP top 10 vulnerabilities.
  Sub-skill of analyze-codebase — executed inline by the orchestrator.
  Also used in --plugin mode for adapted plugin security analysis.
allowed-tools: ["Read", "Grep", "Glob", "Bash"]
---

# Scan Security

## Purpose

Analyze the codebase for security vulnerabilities aligned with the OWASP Top 10, including hardcoded secrets, injection vectors, XSS, authentication/authorization gaps, insecure deserialization, and sensitive data exposure.


## Input

- `PROJECT_PATH`: Root directory of the project being analyzed
- `STACK`: Detected language/framework (from Phase 1)
- `LANGUAGE_PROFILE`: Loaded language profile reference
- `FRAMEWORK_PROFILE`: Loaded framework profile reference (if applicable)
- `SCAN_REPORTS_DIR`: Path to `.code-analysis/scan-reports/` (for loading previous findings)
- `CHANGED_FILES`: Array of relative file paths changed since last scan, or null
- `MODE`: "plugin" when running in plugin analysis mode, absent otherwise
- `PLUGIN_PROFILES_DIR`: Path to `references/plugin-profiles/` (only when MODE=plugin)

### Mode Branch

If `MODE=plugin`:
- Execute Step 1 (hardcoded secrets) normally but scoped to all plugin files
- Skip Steps 2–5 (injection, XSS, CSRF, auth). Execute Plugin Security steps instead.

### Plugin Security Steps (MODE=plugin only)

#### Step P1 — Scan Hook Scripts for Credentials
In plugin contexts, hook scripts often handle CI/CD operations and may contain deployment credentials.
1. Glob hooks/**/*.sh, hooks/**/*.js, hooks/**/*.py
2. Grep for secret patterns: API_KEY, password, token, secret assignments
3. Grep for hardcoded URLs with credentials
4. Severity: **critical** for confirmed secrets

#### Step P2 — Validate ${CLAUDE_PLUGIN_ROOT} Usage
Hardcoded paths break plugin portability when installed on other machines.
1. Grep all hook scripts and MCP configs for hardcoded absolute paths
2. Flag any path that should use ${CLAUDE_PLUGIN_ROOT} instead
3. Severity: **high** for hardcoded paths (portability and security risk)

#### Step P3 — Check .local.md Credential Exposure
The .local.md convention stores user-specific secrets that must never be committed.
1. Grep for .local.md patterns — verify they're in .gitignore
2. Check if any .local.md files are tracked in git (`git ls-files` with .local.md pattern)
3. Verify .gitignore contains appropriate exclusions for credential files
4. Severity: **critical** for tracked credential files, **high** for missing .gitignore entries

#### Step P4 — Check MCP Security
MCP servers may connect to external services — insecure transport exposes credentials in transit.
1. Read MCP server configs (`.mcp.json`, plugin.json `mcp` field) for non-HTTPS/WSS URLs
2. Flag HTTP/WS connections: severity **high** (data in transit exposure)
3. Check for hardcoded auth tokens in MCP configs: severity **critical**
4. Verify MCP server entry points do not expose internal file paths in error messages

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
   - **Python**: `open(request.args`, `pathlib.Path(user_input)`, `shutil.copy(src=user_input`
   - **TypeScript/JS**: `fs.readFile(req.params`, `path.resolve(req.query`, `fs.createReadStream(userPath`
   - **C#**: `File.ReadAllText(userInput)`, `Directory.GetFiles(userInput)`, `new StreamReader(path)`
   - **Go**: `os.Open(r.FormValue(`, `filepath.Join(baseDir, userInput)` without `filepath.Clean`
2. Check for directory listing exposure: static file serving with directory browsing enabled
3. Severity: **critical** for path traversal with user input, **high** for directory listing exposure

### Step 7 — Check HTTP Requests (SSRF)

1. Grep for user-controlled URLs in outbound HTTP requests:
   - `requests.get(user_input`, `fetch(user_input`, `HttpClient` with user-provided URL
   - URL construction from user input without allowlist validation
   - **Python**: `urllib.request.urlopen(user_url)`, `httpx.get(user_url)`
   - **TypeScript/JS**: `axios.get(userUrl)`, `got(userUrl)`, `new URL(userInput)`
   - **C#**: `new HttpRequestMessage(HttpMethod.Get, userUrl)`, `WebRequest.Create(userUrl)`
   - **Go**: `http.Get(userURL)`, `http.NewRequest("GET", userURL, nil)`
2. Check for URL validation: presence of allowlists, blocklists, or URL parsing before requests
3. Severity: **high** for SSRF vectors without URL validation

### Step 8 — Check Logging for Sensitive Data

1. Grep for sensitive data in log statements:
   - `log.*(password`, `log.*(token`, `log.*(secret`, `log.*(credit_card`, `log.*(ssn`
   - `console.log(.*password`, `logger.info(.*token`
   - Request/response body logging without field filtering
   - **Python**: `logging.debug(.*request.data`, `print(.*password`
   - **TypeScript/JS**: `console.log(.*req.body`, `winston.info(.*credentials`
   - **C#**: `_logger.LogDebug(.*Password`, `Trace.Write(.*token`
   - **Go**: `log.Printf(.*password`, `slog.Info(.*token`
2. Severity: **high** for passwords/tokens in logs, **medium** for PII in logs

### Step 9 — Check Security Headers

1. Grep for CORS configuration:
   - Overly permissive: `Access-Control-Allow-Origin: *`, `AllowAnyOrigin()`, `cors({ origin: '*' })`
   - Missing CORS configuration entirely on API endpoints
2. Check for Content Security Policy (CSP): Grep for `Content-Security-Policy` header configuration
3. Check for other security headers: `X-Content-Type-Options`, `X-Frame-Options`, `Strict-Transport-Security`
4. Severity: **high** for wildcard CORS on authenticated endpoints, **medium** for missing security headers

### Step 10 — Check for Known Vulnerabilities (CVE)

1. Use Context7 MCP (resolve-library-id then query-docs) to query for known security advisories on detected dependencies
2. If Context7 is unavailable, use Bash to run ecosystem-specific audit commands:
   - **Node.js**: `npm audit --json` (if package-lock.json exists)
   - **Python**: `pip-audit --format=json` or `safety check --json` (if available)
   - **C#**: `dotnet list package --vulnerable --format json` (if SDK is available)
3. For each vulnerability found, record: CVE ID (if available), affected package, severity from advisory, fixed version
4. Severity: Map from advisory severity — **critical**, **high**, **medium**, **low**

### Step 11 — Produce Findings

Follow the produce-findings template at `${CLAUDE_PLUGIN_ROOT}/references/produce-findings-template.md`. Use ID prefix `SEC-` and dimension `"security"`.

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
- [ ] Known CVE vulnerabilities queried (via Context7 or CLI audit)
- [ ] All findings match the Finding schema
- [ ] Findings array returned to orchestrator

## Scanner Protocol

Read and follow the shared scanner protocol at `${CLAUDE_PLUGIN_ROOT}/references/scanner-protocol.md` for:
- Finding ID generation (deterministic fingerprint IDs)
- Carry-forward protocol (verify previous findings, discover new ones)

## Self-Scoring & Persistence (v0.8.0)

After generating all findings, compute and include the dimension score in the response:

1. Count findings by severity (exclude info): critical, high, medium, low
2. Compute raw penalty: `raw = 3×critical + 2×high + 1×medium + 0.5×low`
3. Compute score: `score = max(1.0, 10 - min(raw, 9))`
4. Include in response header alongside findings:
   ```json
   { "dimension": "security", "score": <score>, "raw_penalty": <raw>, "summary": {...}, "findings": [...] }
   ```
5. Persist findings to `SCAN_REPORTS_DIR/YYYY-MM-DD-security.json` (overwrite if same date exists)
