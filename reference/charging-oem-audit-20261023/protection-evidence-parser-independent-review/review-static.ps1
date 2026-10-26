$ErrorActionPreference = 'Stop'
$reviewRoot = Split-Path -Parent $PSCommandPath
$parentRoot = Split-Path -Parent $reviewRoot
$subjectRoot = Join-Path $parentRoot 'protection-evidence-parser-candidate'
$providerRoot = Join-Path $parentRoot 'protection-query-observer-candidate'
function FileSha([string]$path) { (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant() }
$deliveryPath = Join-Path $subjectRoot 'delivery.json'
$expectedDelivery = 'cd351b4f3b4268e73111f12229584104c8ade7d8b7a75026078550263f876204'
if ((FileSha $deliveryPath) -ne $expectedDelivery) { throw 'subject delivery changed' }
$delivery = Get-Content -LiteralPath $deliveryPath -Raw | ConvertFrom-Json
$bound = [ordered]@{}
foreach ($item in $delivery.files.PSObject.Properties) {
    $path = Join-Path $subjectRoot $item.Name
    $actual = FileSha $path
    $size = (Get-Item -LiteralPath $path).Length
    if ($actual -ne $item.Value.sha256 -or $size -ne $item.Value.bytes) { throw ('delivery mismatch: ' + $item.Name) }
    $bound[$item.Name] = [ordered]@{ sha256=$actual; bytes=$size; delivery_match=$true }
}
$receipt = Get-Content -LiteralPath (Join-Path $subjectRoot 'test-result.json') -Raw | ConvertFrom-Json
if (-not $receipt.passed -or $receipt.new_case_count -ne 26 -or $receipt.cases.Count -ne 26 -or $receipt.cli_returncode -ne 0) { throw 'unexpected author receipt' }
if (@($receipt.cases | Where-Object { -not $_.passed }).Count) { throw 'author failure in receipt' }
foreach ($item in $receipt.files.PSObject.Properties) {
    if ((FileSha (Join-Path $subjectRoot $item.Name)) -ne $item.Value) { throw ('test source mismatch: ' + $item.Name) }
}
$sources = [ordered]@{}
foreach ($name in @('gauge-protocol.h', 'gauge-i2c.h', 'samurai-gauge-protection.c', 'test-observer.c')) {
    $path = Join-Path $providerRoot $name
    $actual = FileSha $path
    $recorded = @($receipt.source_input_sha256.PSObject.Properties | Where-Object { $_.Name.EndsWith('/protection-query-observer-candidate/' + $name) })
    if ($recorded.Count -ne 1 -or $recorded[0].Value -ne $actual) { throw ('provider source mismatch: ' + $name) }
    $sources[$name] = $actual
}
if ($sources['gauge-protocol.h'] -ne $delivery.provider_header.sha256) { throw 'provider header pin mismatch' }
$maskPath = Join-Path $parentRoot 'tca-classifier/tca-reference.h'
if ((FileSha $maskPath) -ne $delivery.classifier_mask_source.sha256) { throw 'mask source mismatch' }
$result = [ordered]@{
    schema='samurai-protection-saved-evidence-independent-review-v1'
    status='accepted_within_offline_saved_text_scope'
    new_blocking_findings=@()
    subject_delivery_sha256=$expectedDelivery
    files=$bound
    provider_source_bindings=$sources
    classifier_mask_source_sha256=(FileSha $maskPath)
    classifier_mask='0xd860'
    author_receipt=[ordered]@{passed=$receipt.passed; new_case_count=$receipt.new_case_count; actual_output_modes=13; rejection_cases=13; cli_returncode=$receipt.cli_returncode; inspected_not_rerun=$true}
    reviewed_properties=@('complete requires all eight full valid frames plus 2719 and two valid BatteryStatus endpoints', 'complete malformed raw retained with matching negative validation errno', 'short or failed transfer raw unavailable', 'valid endpoint times ordered inside batch', 'unattempted and unvisited provider cache layouts accepted', 'mask endpoint stability separate from completion and acceptance', 'C decoder reuses actual provider validator')
    provenance_verified=$false
    freshness_verified=$false
    compatibility_verified=$false
    TCA_classification_verified=$false
    physical_safety_accepted=$false
    new_counterexample_tests_run=0
    author_entrypoints_or_tests_run=$false
    build_or_storage_guard_used=$false
    device_or_transport_accessed=$false
    author_files_modified=$false
    author_delivery_unchanged=((FileSha $deliveryPath) -eq $expectedDelivery)
    review_files=[ordered]@{ 'review.md'=(FileSha (Join-Path $reviewRoot 'review.md')); 'review-static.ps1'=(FileSha $PSCommandPath) }
}
$json = $result | ConvertTo-Json -Depth 8
[System.IO.File]::WriteAllText((Join-Path $reviewRoot 'review-result.json'), $json + "`n", [System.Text.UTF8Encoding]::new($false))
[ordered]@{status=$result.status; result_sha256=(FileSha (Join-Path $reviewRoot 'review-result.json')); subject_delivery_unchanged=$result.author_delivery_unchanged} | ConvertTo-Json
