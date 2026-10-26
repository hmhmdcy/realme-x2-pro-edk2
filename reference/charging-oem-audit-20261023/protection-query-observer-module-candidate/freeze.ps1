$ErrorActionPreference = 'Stop'
$Here = $PSScriptRoot
function Digest([string]$Path) { (Get-FileHash -Algorithm SHA256 -LiteralPath $Path).Hash.ToLowerInvariant() }
function SaveJson([string]$Path, $Value) { [IO.File]::WriteAllText($Path, (($Value | ConvertTo-Json -Depth 30) + "`n"), [Text.UTF8Encoding]::new($false)) }
$ReportPath = Join-Path $Here 'ko-result.json'
if ((Digest $ReportPath) -ne '9626534ca5d7c91d2e4aad87ef462f76bf193899fd903c36be80950cbd796437') { throw 'link receipt changed' }
$Report = Get-Content -Raw -LiteralPath $ReportPath | ConvertFrom-Json
if (-not ($Report.passed -and $Report.tracked_inputs_unchanged -and $Report.actual_config_values_exact_Image502 -and $Report.generated_autoconf_exact_Image502 -and $Report.imports_all_from_Image502_builtin)) { throw 'link receipt not passed' }
if ($Report.intree -ne 'Y' -or $Report.strong_import_count -ne 31 -or $Report.unresolved_strong_imports.Count -ne 0 -or $Report.diagnostics.Count -ne 0) { throw 'module validation mismatch' }
foreach ($Command in $Report.commands) { if (-not $Command.terminal -or $Command.returncode -ne 0) { throw 'original child not terminal zero' } }
if ((Digest (Join-Path $Here 'build-ko.py')) -ne $Report.builder_sha256) { throw 'builder changed' }
$Ko = 'E:/edk2-samurai-out/charging-management-20261023/protection-query-observer-module-private-01/samurai-gauge-protection-observer-private.ko'
$Note = Join-Path (Split-Path -Parent $Ko) 'note.gnu.build-id'
if ((Digest $Ko) -ne $Report.module_sha256 -or (Get-Item -LiteralPath $Ko).Length -ne $Report.module_bytes) { throw 'exported actual ko differs' }
if ((Digest $Note) -ne $Report.module_note_sha256 -or (Get-Item -LiteralPath $Note).Length -ne $Report.module_note_bytes) { throw 'exported actual note differs' }
$Identity = [ordered]@{
 schema='samurai-protection-observer-module-v1'; name='samurai_gauge_protection'; target='/lib/modules/7.3.0-rc6-rmx1931-samurai-k363+/extra/samurai-charging/samurai-gauge-protection.ko';
 private_module_path=$Ko; module_sha256=$Report.module_sha256; module_bytes=$Report.module_bytes; module_note_sha256=$Report.module_note_sha256; GNU_build_id=$Report.GNU_build_id;
 ELF_machine=$Report.ELF_machine; intree=$Report.intree; release=$Report.release; vermagic=$Report.vermagic;
 expected_Image_sha256='085d03066983a82d1d1c74b74f69c85560698d6fc49f62d6db511a8799b25955'; actual_config_sha256=$Report.config_sha256; actual_Image502_exports_sha256=$Report.Image502_exports_sha256;
 strong_import_count=$Report.strong_import_count; all_strong_imports_from_Image502_builtin=$Report.imports_all_from_Image502_builtin; unresolved_strong_imports=@(); import_map_sha256=$Report.import_map_sha256;
 sources=$Report.sources; source_delivery_sha256=$Report.source_delivery_sha256; ko_result_sha256=(Digest $ReportPath); installed_or_loaded=$false; new2719_semantics_or_health_policy_changed=$false; default_extended_query_IO=$false
}
SaveJson (Join-Path $Here 'module-identity.json') $Identity
$Files = [ordered]@{}
foreach ($Item in (Get-ChildItem -LiteralPath $Here -File | Where-Object Name -ne 'delivery.json' | Sort-Object Name)) {
 $Files[$Item.Name] = [ordered]@{sha256=(Digest $Item.FullName); bytes=$Item.Length}
}
$Delivery = [ordered]@{status='actual_private_Image502_intree_module_linked_not_loaded_or_installed';files=$Files; module_identity_sha256=(Digest (Join-Path $Here 'module-identity.json'));module_sha256=$Report.module_sha256;module_bytes=$Report.module_bytes;module_note_sha256=$Report.module_note_sha256;source_candidate_modified=$false;old21_codec149_or_other_suites_rerun=$false;device_SSH_USB_SDK_Git_install_or_reboot=$false;new_Image_or_cohort_created=$false;original_commands_waited_terminal_zero=$true;tracked_inputs_unchanged=$Report.tracked_inputs_unchanged}
SaveJson (Join-Path $Here 'delivery.json') $Delivery
[ordered]@{delivery_sha256=(Digest (Join-Path $Here 'delivery.json'));identity_sha256=(Digest (Join-Path $Here 'module-identity.json'));ko_result_sha256=(Digest $ReportPath);module_sha256=$Report.module_sha256;module_note_sha256=$Report.module_note_sha256} | ConvertTo-Json
