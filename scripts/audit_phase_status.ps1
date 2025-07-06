param(
    [int]   $ApiPort    = 8080,
    [string]$HealthPath = "/healthz",
    [string]$MinioAlias = $Env:MINIO_ALIAS
)

function Pass { param($m) Write-Host "  [PASS]  $m" -ForegroundColor Green }
function Fail { param($m) Write-Host "  [FAIL]  $m" -ForegroundColor Red; exit 1 }

# Phase 0
Write-Host "`nPHASE 0 — Core Services" -ForegroundColor Cyan
$services = @{ postgres="data"; rabbit="messaging"; minio="storage"; qdrant="vector" }
foreach ($n in $services.Keys) {
    $pods = kubectl get pods -n $services[$n] --no-headers
    if (-not $pods) { Fail "$n missing in namespace $($services[$n])" }
    if ($pods -notmatch "$n.*Running") { Fail "$n pod not Running" }
    Pass "$n pod Running"
}

# Phase 0b
Write-Host "`nPHASE 0b — FastAPI health" -ForegroundColor Cyan
try {
    Invoke-WebRequest "http://localhost:$ApiPort$HealthPath" -UseBasicParsing -TimeoutSec 3 | Out-Null
    Pass "FastAPI $HealthPath OK"
} catch {
    Fail "FastAPI health check failed: $_"
}

# Phase 1
Write-Host "`nPHASE 1 — Airflow heartbeat" -ForegroundColor Cyan
$pod = kubectl get pods -n orchestration -o name |
       Where-Object { $_ -match 'airflow-postgresql' } |
       ForEach-Object { $_.Split('/')[1] } |
       Select-Object -First 1
if (-not $pod) { Fail "airflow-postgresql pod not found" }

$sql = "SELECT state FROM dag_run WHERE dag_id='sys_heartbeat' ORDER BY execution_date DESC LIMIT 1;"
$execArgs = @(
    "sh",
    "-c",
    "PGPASSWORD=\$POSTGRES_PASSWORD psql -h 127.0.0.1 -U postgres -d postgres -t -c `"$sql`""
)
$state = kubectl exec -n orchestration $pod -- $execArgs
$state = $state.Trim()
if ($state -eq "success") { Pass "sys_heartbeat last run = success" }
else { Fail "sys_heartbeat state = '$state'" }

# Phase 2
Write-Host "`nPHASE 2 — prospect_queue" -ForegroundColor Cyan
$core = kubectl get pods -n data -o name |
        Where-Object { $_ -match 'postgres-postgresql-0' } |
        ForEach-Object { $_.Split('/')[1] } |
        Select-Object -First 1
if (-not $core) { Fail "core postgres pod not found" }

$pq = kubectl exec -n data $core -- psql -U postgres -d realestate -t -c "SELECT COUNT(*) FROM prospect_queue;" | ForEach { $_.Trim() }
if ([int]$pq -gt 0) { Pass "prospect_queue rows = $pq" } else { Fail "prospect_queue empty" }

# Phase 3
Write-Host "`nPHASE 3 — property_enrichment" -ForegroundColor Cyan
$en = kubectl exec -n data $core -- psql -U postgres -d realestate -t -c "SELECT COUNT(*) FROM property_enrichment;" | ForEach { $_.Trim() }
if ([int]$en -gt 0) { Pass "property_enrichment rows = $en" } else { Fail "property_enrichment empty" }

# Phase 4
Write-Host "`nPHASE 4 — property_scores" -ForegroundColor Cyan
$sc = kubectl exec -n data $core -- psql -U postgres -d realestate -t -c "SELECT COUNT(*) FROM property_scores;" | ForEach { $_.Trim() }
if ([int]$sc -gt 0) { Pass "property_scores rows = $sc" } else { Fail "property_scores empty" }

if ($MinioAlias) {
    & mc ls "$MinioAlias/models/lightgbm/latest.txt" 2>$null
    if ($LASTEXITCODE -eq 0) { Pass "LightGBM model in MinIO" } else { Fail "LightGBM model missing" }
}

# Phase 5
Write-Host "`nPHASE 5 — action_packets" -ForegroundColor Cyan
$ap = kubectl exec -n data $core -- psql -U postgres -d realestate -t -c "SELECT COUNT(*) FROM action_packets;" | ForEach { $_.Trim() }
if ([int]$ap -gt 0) { Pass "action_packets rows = $ap" } else { Fail "action_packets empty" }

if ($MinioAlias) {
    $pdf = kubectl exec -n data $core -- psql -U postgres -d realestate -t -A -c "SELECT packet_path FROM action_packets LIMIT 1;" | ForEach { $_.Trim() }
    & mc ls "$MinioAlias/$pdf" 2>$null
    if ($LASTEXITCODE -eq 0) { Pass "sample PDF in MinIO ($pdf)" } else { Fail "sample PDF missing ($pdf)" }
}

Write-Host "`nALL PHASE CHECKS PASSED" -ForegroundColor Green
