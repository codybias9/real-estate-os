# Complete Runtime Verification & PR Evidence Collection
# Run this script in PowerShell on Windows where Docker Desktop is running

$ErrorActionPreference = "Stop"

Write-Host "==============================================" -ForegroundColor Cyan
Write-Host "Runtime Verification & PR Evidence Collection" -ForegroundColor Cyan
Write-Host "==============================================" -ForegroundColor Cyan
Write-Host ""

#------------------------------------------------------------------------------
# A. Auto-locate repo root & branch; prep artifacts dir
#------------------------------------------------------------------------------
Write-Host "Phase A: Locating repository and preparing artifacts..." -ForegroundColor Yellow

# Find repo root
$repoRoot = git rev-parse --show-toplevel 2>$null
if (-not $repoRoot) {
    $repoRoot = Get-Location
}
Set-Location $repoRoot

# Ensure correct branch
git fetch --all --prune --quiet 2>$null
$currentBranch = git rev-parse --abbrev-ref HEAD

$targetBranch = "claude/audit-wiring-readiness-014VYQdX46CD1u2s6KGWqbGw"
if ($currentBranch -ne $targetBranch) {
    Write-Host "Switching to $targetBranch..." -ForegroundColor Gray
    git checkout $targetBranch
    git pull --rebase 2>$null
}

# Artifacts directory
$artDir = "artifacts\pr_evidence"
New-Item -ItemType Directory -Force -Path $artDir | Out-Null

$repoRoot | Out-File -FilePath "$artDir\repo_root.txt" -Encoding UTF8
git rev-parse --abbrev-ref HEAD | Out-File -FilePath "$artDir\branch.txt" -Encoding UTF8
$commitSha = git rev-parse HEAD
$commitSha | Out-File -FilePath "$artDir\commit_sha.txt" -Encoding UTF8

Write-Host "✓ Phase A complete" -ForegroundColor Green
Write-Host "  - Repo root: $repoRoot"
Write-Host "  - Branch: $targetBranch"
Write-Host "  - Commit: $commitSha"
Write-Host ""

#------------------------------------------------------------------------------
# B. Bring up services (or confirm they're up) & wait until healthy
#------------------------------------------------------------------------------
Write-Host "Phase B: Verifying Docker services are running..." -ForegroundColor Yellow

# Check for compose file
$composeFile = "docker-compose.yaml"
if (-not (Test-Path $composeFile)) {
    $composeFile = "docker-compose.yml"
}

# Start services (idempotent)
Write-Host "Ensuring services are up: docker compose -f $composeFile up -d"
docker compose -f $composeFile up -d

# Wait for API health
$apiUrl = "http://localhost:8000"
Write-Host "Waiting for API at $apiUrl ..." -ForegroundColor Gray
"Waiting for API at $apiUrl ..." | Out-File -FilePath "$artDir\wait_api.log" -Encoding UTF8

for ($i = 1; $i -le 60; $i++) {
    try {
        $response = Invoke-WebRequest -Uri "$apiUrl/api/v1/healthz" -Method GET -UseBasicParsing -TimeoutSec 2 -ErrorAction SilentlyContinue
        if ($response.StatusCode -eq 200) {
            Write-Host "✓ API is up and healthy!" -ForegroundColor Green
            "✓ API is up and healthy!" | Out-File -FilePath "$artDir\wait_api.log" -Append -Encoding UTF8
            break
        }
    } catch {
        # Ignore and retry
    }

    if ($i -eq 60) {
        Write-Host "❌ API did not become healthy after 120 seconds" -ForegroundColor Red
        Write-Host "Please check: docker compose logs api" -ForegroundColor Red
        exit 1
    }
    Start-Sleep -Seconds 2
}
Write-Host ""

#------------------------------------------------------------------------------
# C. OpenAPI & endpoint count + tag verification
#------------------------------------------------------------------------------
Write-Host "Phase C: Collecting OpenAPI spec and verifying coverage..." -ForegroundColor Yellow

Invoke-WebRequest -Uri "$apiUrl/openapi.json" -OutFile "$artDir\openapi.json" -UseBasicParsing

# Parse OpenAPI using Python
$pythonScript = @"
import json
with open('artifacts/pr_evidence/openapi.json') as f:
    spec = json.load(f)
paths_count = len(spec.get('paths', {}))
tags = [t.get('name') for t in spec.get('tags', [])]
summary = {
    'paths': paths_count,
    'tags': tags,
    'has_workflow': 'workflow' in tags,
    'has_automation': 'automation' in tags,
    'has_data': 'data' in tags,
    'has_system': 'system' in tags
}
print(json.dumps(summary, indent=2))
"@

$openapiSummary = python -c $pythonScript
$openapiSummary | Out-File -FilePath "$artDir\openapi_summary.json" -Encoding UTF8
Write-Host $openapiSummary

Write-Host "✓ Phase C complete" -ForegroundColor Green
Write-Host ""

#------------------------------------------------------------------------------
# D. Auth flip & write-guard checks (401→200)
#------------------------------------------------------------------------------
Write-Host "Phase D: Testing auth flip and write guard..." -ForegroundColor Yellow

# 1) PATCH without token (expect 401/403)
Write-Host "Testing PATCH without token (expect 401/403)..."
try {
    $response = Invoke-WebRequest -Uri "$apiUrl/api/v1/properties/demo-1" -Method PATCH `
        -ContentType "application/json" `
        -Body '{"nickname":"demo"}' `
        -UseBasicParsing -ErrorAction SilentlyContinue
    $noTokenCode = $response.StatusCode
} catch {
    $noTokenCode = $_.Exception.Response.StatusCode.value__
}

$noTokenCode | Out-File -FilePath "$artDir\auth_flip_summary.txt" -Encoding UTF8
Write-Host "  Result: $noTokenCode"

# 2) Login to get token
Write-Host "Logging in to get auth token..."
try {
    $loginResponse = Invoke-RestMethod -Uri "$apiUrl/api/v1/auth/login" -Method POST `
        -ContentType "application/json" `
        -Body '{"email":"demo@example.com","password":"demo123"}' `
        -UseBasicParsing
    $token = $loginResponse.access_token
    $token | Out-File -FilePath "$artDir\token.txt" -Encoding UTF8
    $loginResponse | ConvertTo-Json | Out-File -FilePath "$artDir\login.json" -Encoding UTF8
} catch {
    Write-Host "❌ Failed to login" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    exit 1
}

# 3) PATCH with token (expect 200/204)
Write-Host "Testing PATCH with token (expect 200/204)..."
try {
    $response = Invoke-WebRequest -Uri "$apiUrl/api/v1/properties/demo-1" -Method PATCH `
        -Headers @{ "Authorization" = "Bearer $token" } `
        -ContentType "application/json" `
        -Body '{"nickname":"demo"}' `
        -UseBasicParsing -ErrorAction SilentlyContinue
    $withTokenCode = $response.StatusCode
    $response.Content | Out-File -FilePath "$artDir\patch_with_token.json" -Encoding UTF8
} catch {
    $withTokenCode = $_.Exception.Response.StatusCode.value__
}

Write-Host "  Result: $withTokenCode"
"SUMMARY:" | Out-File -FilePath "$artDir\auth_flip_summary.txt" -Append -Encoding UTF8
"  - PATCH without token: $noTokenCode (expect 401/403)" | Out-File -FilePath "$artDir\auth_flip_summary.txt" -Append -Encoding UTF8
"  - PATCH with token: $withTokenCode (expect 200/204)" | Out-File -FilePath "$artDir\auth_flip_summary.txt" -Append -Encoding UTF8

Write-Host "✓ Phase D complete" -ForegroundColor Green
Write-Host ""

#------------------------------------------------------------------------------
# E. CORS sanity (preflight + simple GET)
#------------------------------------------------------------------------------
Write-Host "Phase E: Verifying CORS headers..." -ForegroundColor Yellow

Write-Host "Testing CORS preflight (OPTIONS)..."
try {
    $response = Invoke-WebRequest -Uri "$apiUrl/api/v1/properties" -Method OPTIONS `
        -Headers @{
            "Origin" = "http://localhost:3000"
            "Access-Control-Request-Method" = "GET"
            "Access-Control-Request-Headers" = "content-type,authorization"
        } -UseBasicParsing -ErrorAction SilentlyContinue
    $response.RawContent | Out-File -FilePath "$artDir\cors_preflight_headers.txt" -Encoding UTF8
} catch {
    # May not support OPTIONS
}

Write-Host "Testing CORS on GET request..."
try {
    $response = Invoke-WebRequest -Uri "$apiUrl/api/v1/healthz" `
        -Headers @{ "Origin" = "http://localhost:3000" } `
        -UseBasicParsing
    $response.RawContent | Out-File -FilePath "$artDir\cors_get_headers.txt" -Encoding UTF8
    $response.Content | Out-File -FilePath "$artDir\cors_get_body.json" -Encoding UTF8

    if ($response.Headers["Access-Control-Allow-Origin"]) {
        Write-Host "✓ CORS headers present" -ForegroundColor Green
    } else {
        Write-Host "⚠ CORS headers not found" -ForegroundColor Yellow
    }
} catch {
    Write-Host "⚠ Could not verify CORS" -ForegroundColor Yellow
}

Write-Host "✓ Phase E complete" -ForegroundColor Green
Write-Host ""

#------------------------------------------------------------------------------
# F. SSE proof (headless): open stream, emit, capture one event
#------------------------------------------------------------------------------
Write-Host "Phase F: Testing SSE stream end-to-end..." -ForegroundColor Yellow

$sseStream = "$artDir\sse_stream.jsonl"
Remove-Item -Path $sseStream -ErrorAction SilentlyContinue

# Start SSE stream in background job
Write-Host "Opening SSE stream..."
$sseJob = Start-Job -ScriptBlock {
    param($url, $outFile)
    try {
        $request = [System.Net.HttpWebRequest]::Create($url)
        $request.Accept = "text/event-stream"
        $request.Timeout = 10000
        $response = $request.GetResponse()
        $stream = $response.GetResponseStream()
        $reader = New-Object System.IO.StreamReader($stream)

        $startTime = Get-Date
        while (((Get-Date) - $startTime).TotalSeconds -lt 10) {
            $line = $reader.ReadLine()
            if ($line) {
                Add-Content -Path $outFile -Value $line
            }
        }
    } catch {
        # Timeout or connection closed
    }
} -ArgumentList "$apiUrl/api/v1/sse/stream", $sseStream

Start-Sleep -Seconds 2

# Emit test event
Write-Host "Emitting test event..."
try {
    $emitResponse = Invoke-WebRequest -Uri "$apiUrl/api/v1/sse/test/emit" -Method POST `
        -ContentType "application/json" `
        -Body '{"event_type":"property_updated","data":{"id":"pr-verify-123","source":"pr-evidence"}}' `
        -UseBasicParsing
    $emitCode = $emitResponse.StatusCode
    $emitResponse.Content | Out-File -FilePath "$artDir\sse_emit_resp.json" -Encoding UTF8
} catch {
    $emitCode = "000"
}

Write-Host "  Emit response code: $emitCode"
$emitCode | Out-File -FilePath "$artDir\sse_emit_code.txt" -Encoding UTF8

# Wait for event to be received
Start-Sleep -Seconds 3

# Stop the SSE stream job
Stop-Job -Job $sseJob -ErrorAction SilentlyContinue
Remove-Job -Job $sseJob -Force -ErrorAction SilentlyContinue

# Show captured stream
Write-Host "Captured SSE stream (first 10 lines):"
if (Test-Path $sseStream) {
    $streamContent = Get-Content $sseStream -First 10
    $streamContent | Out-File -FilePath "$artDir\sse_stream_head.txt" -Encoding UTF8
    Write-Host $streamContent

    if ($streamContent -match "data:") {
        Write-Host "✓ SSE event received!" -ForegroundColor Green
    } else {
        Write-Host "⚠ No SSE events captured" -ForegroundColor Yellow
    }
} else {
    Write-Host "⚠ No SSE stream captured" -ForegroundColor Yellow
    "(no stream lines captured)" | Out-File -FilePath "$artDir\sse_stream_head.txt" -Encoding UTF8
}

Write-Host "✓ Phase F complete" -ForegroundColor Green
Write-Host ""

#------------------------------------------------------------------------------
# G. Minimal page-walk proxy (API only)
#------------------------------------------------------------------------------
Write-Host "Phase G: Testing API endpoints for all 6 pages..." -ForegroundColor Yellow

$endpoints = @(
    "$apiUrl/api/v1/workflow/smart-lists",
    "$apiUrl/api/v1/automation/cadence-rules",
    "$apiUrl/api/v1/leads",
    "$apiUrl/api/v1/deals",
    "$apiUrl/api/v1/data/summary",
    "$apiUrl/api/v1/system/health"
)

$pageWalkResults = @()
foreach ($url in $endpoints) {
    try {
        $response = Invoke-WebRequest -Uri $url -Method GET -UseBasicParsing -TimeoutSec 5 -ErrorAction SilentlyContinue
        $code = $response.StatusCode
    } catch {
        $code = if ($_.Exception.Response) { $_.Exception.Response.StatusCode.value__ } else { "000" }
    }
    $result = "  $url → $code"
    Write-Host $result
    $pageWalkResults += $result
}

$pageWalkResults | Out-File -FilePath "$artDir\page_walk.txt" -Encoding UTF8

Write-Host "✓ Phase G complete" -ForegroundColor Green
Write-Host ""

#------------------------------------------------------------------------------
# H. Gate evaluation & PR body
#------------------------------------------------------------------------------
Write-Host "Phase H: Evaluating gates and generating PR body..." -ForegroundColor Yellow

# Parse OpenAPI summary
$openapiData = Get-Content "$artDir\openapi_summary.json" | ConvertFrom-Json
$paths = $openapiData.paths
$hasWorkflow = $openapiData.has_workflow
$hasAutomation = $openapiData.has_automation
$hasData = $openapiData.has_data
$hasSystem = $openapiData.has_system

# Gate 1: OpenAPI coverage
$g1 = if ($paths -ge 140 -and $hasWorkflow -and $hasAutomation -and $hasData -and $hasSystem) { "PASS" } else { "FAIL" }

# Gate 2: Auth flip
$g2 = if (($noTokenCode -eq 401 -or $noTokenCode -eq 403) -and ($withTokenCode -eq 200 -or $withTokenCode -eq 204)) { "PASS" } else { "FAIL" }

# Gate 3: Write guard
$g3 = if ($noTokenCode -eq 401 -or $noTokenCode -eq 403) { "PASS" } else { "FAIL" }

# Gate 4: CORS
$corsHeaders = Get-Content "$artDir\cors_get_headers.txt" -Raw -ErrorAction SilentlyContinue
$g4 = if ($corsHeaders -match "Access-Control-Allow-Origin") { "PASS" } else { "FAIL" }

# Gate 5: SSE
$sseContent = Get-Content "$artDir\sse_stream.jsonl" -Raw -ErrorAction SilentlyContinue
$g5 = if ($sseContent -match "data:") { "PASS" } else { "FAIL" }

# Write gates summary
$gatesSummary = @"
G1 OpenAPI/tag coverage: $g1 (paths=$paths, workflow=$hasWorkflow, automation=$hasAutomation, data=$hasData, system=$hasSystem)
G2 Auth flip 401→200: $g2 (no_token=$noTokenCode, with_token=$withTokenCode)
G3 Write guard unauth write blocked: $g3 (no_token=$noTokenCode)
G4 CORS headers present: $g4
G5 SSE emit→receive: $g5
"@

$gatesSummary | Out-File -FilePath "$artDir\gates_summary.txt" -Encoding UTF8
Write-Host $gatesSummary

# Generate PR body
$timestamp = (Get-Date).ToUniversalTime().ToString("yyyy-MM-dd HH:mm:ss UTC")
$branch = Get-Content "$artDir\branch.txt" -Raw
$commit = Get-Content "$artDir\commit_sha.txt" -Raw
$openapiJson = Get-Content "$artDir\openapi_summary.json" -Raw
$authFlip = Get-Content "$artDir\auth_flip_summary.txt" -Raw
$sseHead = Get-Content "$artDir\sse_stream_head.txt" -Raw -ErrorAction SilentlyContinue
if (-not $sseHead) { $sseHead = "(no stream lines captured)" }
$pageWalk = Get-Content "$artDir\page_walk.txt" -Raw

$prBody = @"
# Demo Readiness — Runtime Evidence

**Commit:** ``$commit``
**Branch:** ``$branch``
**Verification Date:** $timestamp

## Gate Results

| Gate | Status | Details |
|------|--------|---------|
| **G1** OpenAPI/tag coverage | **$g1** | paths=$paths, workflow=$hasWorkflow, automation=$hasAutomation, data=$hasData, system=$hasSystem |
| **G2** Auth flip 401→200 | **$g2** | no_token=$noTokenCode, with_token=$withTokenCode |
| **G3** Write guard (unauth blocked) | **$g3** | unauth_code=$noTokenCode |
| **G4** CORS headers present | **$g4** | - |
| **G5** SSE emit→receive | **$g5** | - |

## OpenAPI Summary

``````json
$openapiJson
``````

## Auth Flip Details

``````
$authFlip
``````

## SSE Stream Capture (first 10 lines)

``````
$sseHead
``````

## Page Walk (API endpoints)

``````
$pageWalk
``````

---

## Browser-Only Proofs (To Be Verified Manually)

The following checks require browser-based verification:

1. **Auth Banner**: Login → Console shows "🔐 AUTH: Demo token attached"
2. **SSE Badge**: Dashboard header shows **🟢 Connected**
3. **SSE Event Test**: Admin → "Emit Test Event" → Toast appears + Badge flashes
4. **Page Walk**: All 6 pages load with no console errors

### Browser Testing Checklist

- [ ] Login shows auth token in console
- [ ] Dashboard shows SSE badge as "Connected"
- [ ] Admin test event triggers toast notification
- [ ] All pages load: workflow, automation, leads, deals, data, admin
- [ ] No red console errors on any page
- [ ] Network tab shows 200 responses

---

**All artifacts saved to:** ``$artDir\``
"@

$prBody | Out-File -FilePath "$artDir\PR_BODY.md" -Encoding UTF8

Write-Host ""
Write-Host "==============================================" -ForegroundColor Cyan
Write-Host "✓ Evidence Collection Complete!" -ForegroundColor Green
Write-Host "==============================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Gate Summary:"
Write-Host "  G1 (OpenAPI): $g1"
Write-Host "  G2 (Auth flip): $g2"
Write-Host "  G3 (Write guard): $g3"
Write-Host "  G4 (CORS): $g4"
Write-Host "  G5 (SSE): $g5"
Write-Host ""
Write-Host "Next Steps:" -ForegroundColor Yellow
Write-Host "  1. Review: $artDir\PR_BODY.md"
Write-Host "  2. Complete browser-based checks (see PR_BODY.md)"
Write-Host "  3. Take 4 screenshots:"
Write-Host "     - Auth token console log"
Write-Host "     - SSE badge showing Connected"
Write-Host "     - Toast notification appearing"
Write-Host "     - All pages with no errors"
Write-Host "  4. Paste PR_BODY.md into your pull request"
Write-Host ""
Write-Host "All artifacts saved to: $artDir\"
