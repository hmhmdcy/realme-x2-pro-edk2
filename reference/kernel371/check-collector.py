"""Run a real independent collector against owned/unrelated filesystem fixtures."""
from pathlib import Path
import hashlib,json,os,shutil,struct,subprocess,sys,tempfile,time
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
work=Path(tempfile.mkdtemp(prefix='collector-fixture-',dir=P));shutil.copyfile(HERE/'snapshot-collector.py',work/'collector.py');shutil.copyfile(HERE.parent/'kernel368/decode-start-dump.py',work/'dump_decoder.py')
fw=(P.parent/'kernel352/CAMERA_ICP.elf-private').read_bytes();phoff=struct.unpack_from('<I',fw,28)[0];stride,count=struct.unpack_from('<HH',fw,42)
loads=[struct.unpack_from('<8I',fw,phoff+i*stride) for i in range(count)]
segment=next(s for s in loads if s[0]==1 and s[2]==0 and s[4]>=4096);page=fw[segment[1]:segment[1]+4096]
sample=(P.parent/'kernel368/synthetic-devcoredump-private.bin').read_bytes();rows=[]
for case in ['owned','code-mismatch','guard-mismatch','not-held','unrelated-node']:
 base=work/case;root=base/'transaction';root.mkdir(parents=True)
 sysfs=base/'sysfs';sysfs.mkdir();dt=base/'dt';expected=dt/'soc@0/samurai-icp356-boot@ac10000';expected.mkdir(parents=True)
 devices=base/'devices';device=devices/'ac10000.samurai-icp356-boot';device.mkdir(parents=True);(device/'of_node').symlink_to(expected if case!='unrelated-node' else dt)
 module=base/'module';(module/'parameters').mkdir(parents=True);(module/'parameters/hold_start_failure').write_text('Y\n')
 (root/'guard').write_text('fixture-guard\n');(root/'boot-id').write_text('wrong\n' if case=='guard-mismatch' else 'fixture-guard\n')
 meta=dict(boot_guard=str(root/'guard'),boot_id_file=str(root/'boot-id'),firmware_code_page_sha256=hashlib.sha256(page).hexdigest(),firmware_sha256=hashlib.sha256(fw).hexdigest());(root/'manifest.json').write_text(json.dumps(meta))
 with (device/'firmware').open('wb') as f:
  f.truncate(5*1024*1024);f.seek(0);f.write(page if case!='code-mismatch' else bytes(4096))
  f.seek(0x1099a0);f.write(struct.pack('<3I',0x0741c004,0x5,3))
  f.seek(0x340000+(0x07400000>>20)*4);f.write(struct.pack('<I',0x344001))
 state=dict(terminal=True,phase='failed-held',error=-121,cpu_release_attempted=True,cleanup_error=0,cpu_enabled=False,irq_enabled=False,reset_asserted=True,power_held=True,backing_owned=True,mapped_bytes=6414336)
 (module/'parameters/result').write_text('{"terminal":false}')
 child=subprocess.Popen([sys.executable,str(work/'collector.py'),str(root),'--sysfs',str(sysfs),'--dt-base',str(dt),'--module',str(module),'--devices',str(devices),'--seconds','.4'],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
 deadline=time.monotonic()+2
 while not (root/'collector-ready.json').exists() and child.poll() is None and time.monotonic()<deadline:time.sleep(.005)
 assert child.poll() is None and (root/'collector-ready.json').exists()
 other=devices/'unrelated';other.mkdir();(other/'of_node').symlink_to(dt)
 unrelated=sysfs/'devcd0';unrelated.mkdir();(unrelated/'failing_device').symlink_to(other);(unrelated/'data').write_bytes(b'unrelated snapshot')
 owned=sysfs/'devcd1';owned.mkdir();(owned/'failing_device').symlink_to(device);(owned/'data').write_bytes(sample)
 if case!='not-held':(module/'parameters/result').write_text(json.dumps(state))
 deadline=time.monotonic()+2;ack=False
 while child.poll() is None and time.monotonic()<deadline:
  if owned.exists() and (owned/'data').read_bytes()==b'1':
   ack=True;assert (root/'a5-devcd1-private.bin').read_bytes()==sample
   assert json.loads((root/'a5-dump-decoded-private.json').read_text())['init_response']==3
   if case=='owned':assert (root/'firmware-exception-private.bin').exists() and (root/'firmware-l1-private.bin').exists()
   shutil.rmtree(owned)
  time.sleep(.002)
 stdout,stderr=child.communicate(timeout=3);assert child.returncode==0,stderr.decode()
 result=json.loads((root/'collector-result.json').read_text())
 assert (unrelated/'data').read_bytes()==b'unrelated snapshot'
 assert result['snapshot_saved']==(case=='owned'),result
 if case=='owned':
  assert ack and result['owned_snapshot_acknowledged'] and result['snapshot']['code_page_match'] and result['snapshot']['l2_tables']==1
  assert (root/'firmware-code-private.bin').read_bytes()==page
 elif case=='code-mismatch':assert ack and not (root/'firmware-exception-private.bin').exists() and not result.get('error')
 elif case in ['guard-mismatch','unrelated-node']:assert result.get('error') is not None and not ack and not (root/'firmware-code-private.bin').exists()
 elif case=='not-held':assert ack and result['timeout'] and not result['snapshot_attempted'] and not (root/'firmware-code-private.bin').exists()
 rows.append(dict(case=case,snapshot_saved=result['snapshot_saved'],dump_acknowledged=ack,passed=True))
report=dict(stage=371,tests=rows,independent_collector_ready_before_boot_fixture=True,
 verifies_held_state_owner_of_node_and_boot_guard=True,code_page_checked_before_exception_or_page_tables=True,
 only_necessary_bounded_l2_tables_read=True,private_durable_snapshot_and_dump_precede_ack=True,
 unrelated_dump_not_consumed=True,fixture_not_actual_kernel_or_firmware_execution=True,passed=True)
(HERE/'collector-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
