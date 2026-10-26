from pathlib import Path
import hashlib,json,shlex
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
assert (P/'recovery-collected/pstore-console-ramoops-0').exists()
meta=json.loads((P/'manifest-private.json').read_text());boot=json.loads((HERE.parent/'kernel389/build-package-validation.json').read_text());fat=json.loads((HERE.parent/'kernel365/boot-package-validation.json').read_text())
code=r'''from pathlib import Path
import hashlib,json,os
meta=META;boot=BOOT;fat=FAT;sha=lambda p:hashlib.file_digest(Path(p).open('rb'),'sha256').hexdigest()
assert b'realme,samurai' in Path('/sys/firmware/devicetree/base/compatible').read_bytes() and os.uname().release=='7.3.0-rc6-rmx1931-samurai-k363+'
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()!=Path('/var/lib/samurai/k390-active/boot-id-private.txt').read_bytes()
assert sha('/dev/disk/by-partlabel/boot')==boot['boot_sha256'] and sha('/dev/disk/by-partlabel/logdump')==fat['logdump_sha256']
assert all(sha(n)==h for n,h in meta['normal_files'].items())
assert sha('/sys/module/qcom_camss_icp_a5_core/notes/.note.gnu.build-id')==meta['normal_core_note_sha256']
for n,h in meta['unchanged_notes'].items():assert sha('/sys/module/'+n+'/notes/.note.gnu.build-id')==h
assert all(sha('/etc/libcamera/ipa/camss-vfe/'+n)==h for n,h in meta['profiles'].items())
assert not Path('/sys/module/qcom_camss_icp_a5_core/parameters/test_drop_frame_ack').exists()
assert Path('/proc/sys/kernel/tainted').read_text().strip()=='0' and not Path('/proc/13432').exists()
dev=Path('/sys/bus/platform/devices/ac10000.icp');assert (dev/'driver').resolve().name=='qcom-sm8150-icp'
s=json.loads((dev/'m2m_status').read_text());c=json.loads((dev/'state').read_text());assert not any(s[k] for k in ['users','running','fatal','pinned','orphans','jobs'])
assert not any(c[k] for k in ['backing_owned','cpu_enabled','irq_enabled','power_held','mapped_bytes','ipe_dma_pending','request_fw_mapped','imported_buffers','cpu_release_attempted'])
root=Path('/var/lib/samurai/k394-recovered');assert not root.exists();root.mkdir(mode=0o700);guard=root/'boot-id-private.txt'
with guard.open('xb') as f:f.write(Path('/proc/sys/kernel/random/boot_id').read_bytes());f.flush();os.fsync(f.fileno())
fd=os.open(root,os.O_RDONLY|os.O_DIRECTORY)
try:os.fsync(fd)
finally:os.close(fd)
print(json.dumps(dict(stage=394,guard_path=str(guard),new_boot_verified=True,original_key_and_known_hosts_reused=True,boot389_and_logdump365_readback_match=True,normal393_disk_pair_and_loaded_notes_match=True,camss_composite_and_adapter_notes_unchanged=True,private_profiles_unchanged=True,test_knobs_absent=True,old_worker_absent_after_boot_transition=True,probe_did_not_start_firmware=True,m2m=s,passed=True)))
'''.replace('META',repr(meta)).replace('BOOT',repr(boot)).replace('FAT',repr(fat))
q=host.raw_ssh('python3 -c '+shlex.quote(code),timeout=35);(P/'postboot-adoption-private.json').write_bytes(q.stdout);d=json.loads(q.stdout);d.pop('guard_path')
(HERE/'postboot-validation.json').write_text(json.dumps(d,indent=2)+'\n');print(json.dumps(d,indent=2))
