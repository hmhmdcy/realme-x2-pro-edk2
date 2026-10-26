from pathlib import Path
import datetime,hashlib,json,tarfile
ref=Path(__file__).resolve().parent;private=Path('/mnt/e/edk2-samurai-out/kernel191')
before=json.loads((ref/'validity-before-r2-validation.json').read_text());after=json.loads((ref/'validity-after-validation.json').read_text())
wire=json.loads((ref/'injection-wire-validation.json').read_text());injection=json.loads((ref/'assistance-injection-validation.json').read_text())
assert before['duration_hours']==0 and after['duration_hours']==168 and after['start_utc_timestamp']>before['start_utc_timestamp']
assert all(r['ack'] and r['indication'] and r['client_released'] and r['device_closed'] and not r['errors'] for r in [before,after])
assert wire['indication_part_numbers']==list(range(1,51)) and wire['per_part_orders']=={'indication/response':49,'response/indication':1}
assert injection['injection_ack'] and injection['same_mm_owner'] and injection['gps_enabled_final']==0
with tarfile.open(private/'evidence-private.tar.gz') as tar:compilelog=tar.extractfile('k191-mm-build/compile-private.log').read().decode()
warnings=[line for line in compilelog.splitlines() if 'warning:' in line and 'lto-wrapper:' not in line]
assert not warnings,warnings
report=dict(stage=191,full_file_injection_proven=True,standard_mm_dbus_ack=True,bytes=injection['bytes'],chunks_completed=50,firmware_validity_hours_before=0,firmware_validity_hours_after=168,
 firmware_start_utc=datetime.datetime.fromtimestamp(after['start_utc_timestamp'],datetime.timezone.utc).isoformat(),
 early_indication_chunks=49,ack_first_chunks=1,all_indication_part_numbers_match=True,native_compiler_warnings=0,
 native_predicted_orbits_path_fell_back_to_xtra=True,native_predicted_orbits_success_proven=False,utc_and_position_production_callbacks_host_tested=True,
 native_utc_probe_success_and_cleanup=True,gps_fix_proven=False)
(ref/'assistance-end-to-end-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
