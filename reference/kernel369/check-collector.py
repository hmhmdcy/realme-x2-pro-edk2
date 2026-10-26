"""Fixture tests for ownership, durable collection, decoding and acknowledgement."""
from pathlib import Path
import hashlib,json,shutil,subprocess,sys,time
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
work=P/'collector-fixture';assert not work.exists();work.mkdir();root=work/'transaction';root.mkdir();sysfs=work/'sysfs';sysfs.mkdir();dt=work/'dt';expected=dt/'soc@0/samurai-icp356-boot@ac10000';expected.mkdir(parents=True)
device=work/'devices/ac10000.samurai-icp356-boot';device.mkdir(parents=True);(device/'of_node').symlink_to(expected)
shutil.copyfile(HERE/'dump-collector.py',work/'collector.py');shutil.copyfile(HERE.parent/'kernel368/decode-start-dump.py',work/'dump_decoder.py')
child=subprocess.Popen([sys.executable,str(work/'collector.py'),str(root),'--sysfs',str(sysfs),'--dt-base',str(dt),'--seconds','3'],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
deadline=time.monotonic()+2
while not (root/'collector-ready.json').exists() and child.poll() is None and time.monotonic()<deadline:time.sleep(.01)
assert (root/'collector-ready.json').exists() and child.poll() is None
# An unrelated coredump created after readiness must remain untouched.
other=work/'devices/other-device';other.mkdir();(other/'of_node').symlink_to(dt)
unrelated=sysfs/'devcd0';unrelated.mkdir();(unrelated/'failing_device').symlink_to(other);(unrelated/'data').write_bytes(b'unrelated diagnostic')
owned=sysfs/'devcd1';owned.mkdir();(owned/'failing_device').symlink_to(device)
sample=(P.parent/'kernel368/synthetic-devcoredump-private.bin').read_bytes();(owned/'data').write_bytes(sample)
deadline=time.monotonic()+2;ack=False
while child.poll() is None and time.monotonic()<deadline:
 if (owned/'data').read_bytes()==b'1':
  ack=True;assert (root/'a5-devcd1-private.bin').read_bytes()==sample
  assert json.loads((root/'a5-dump-decoded-private.json').read_text())['init_response']==3
  assert owned.resolve().is_relative_to(work.resolve());shutil.rmtree(owned);break
 time.sleep(.005)
stdout,stderr=child.communicate(timeout=4);assert child.returncode==0,stderr.decode()
result=json.loads((root/'collector-result.json').read_text());assert ack and result['captured'] and result['owned_snapshot_acknowledged'] and result['decoded']
assert (unrelated/'data').read_bytes()==b'unrelated diagnostic'
# With no new device, readiness still precedes a bounded timeout.
empty=work/'empty';empty.mkdir();q=subprocess.run([sys.executable,str(work/'collector.py'),str(empty),'--sysfs',str(sysfs),'--dt-base',str(dt),'--seconds','.05'],capture_output=True,timeout=3);assert not q.returncode,q.stderr.decode()
none=json.loads((empty/'collector-result.json').read_text());assert none['terminal'] and not none['captured'] and none['timeout']
report=dict(stage=369,passed=True,collector_process_live_before_dump_creation=True,
    only_matching_new_failing_device_collected=True,unrelated_snapshot_not_consumed=True,
    exact_production_format_decoded=True,raw_and_decoded_files_persisted_before_acknowledgement=True,
    owned_snapshot_device_reference_released_before_return=True,timeout_without_hardware_start_checked=True,
    filesystem_fixture_not_actual_kernel_devcoredump_validation=True)
(HERE/'collector-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
