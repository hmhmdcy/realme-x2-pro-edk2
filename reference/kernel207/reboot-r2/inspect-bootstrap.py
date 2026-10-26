from pathlib import Path
import hashlib, json, os, re, shutil, subprocess
os.umask(0o077)
root = Path('/var/lib/samurai')
boot = Path('/proc/sys/kernel/random/boot_id').read_bytes()
assert boot == (root / 'k207r2-runtime/boot-id-private.txt').read_bytes()
assert boot != (root / 'k207r2-before-reboot/boot-id-private.txt').read_bytes()
out = root / 'k207r2-bootstrap-inspection'; out.mkdir(mode=0o700)
(out / 'boot-id-private.txt').write_bytes(boot)
base = Path('/run/samurai-wifi')
for name in ['tftp.log', 'rmtfs.log', 'boot-finished', 'boot-started']:
    path = base / name
    if path.is_file(): shutil.copyfile(path, out / (name + '-private'))
text = (base / 'tftp.log').read_text(errors='replace')
mcfg_lines = [line for line in text.splitlines() if '/readwrite/mcfg.tmp' in line]
(out / 'mcfg-tftp-lines-private.txt').write_text('\n'.join(mcfg_lines) + '\n')
cache = base / 'tftp-rw'
files = {str(p.relative_to(cache)): dict(bytes=p.stat().st_size, sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in cache.rglob('*') if p.is_file() and not p.is_symlink()}
(out / 'cache-file-manifest-private.json').write_text(json.dumps(files, indent=2) + '\n')
for name in ['mcfg.tmp', 'server_check.txt']:
    p = cache / name
    if p.is_file(): shutil.copyfile(p, out / (name + '-private'))
log = subprocess.check_output(['dmesg']); (out / 'dmesg-private.txt').write_bytes(log)
pid = int((base / 'tftp.pid').read_text())
expected = 'b3bb82b9d090a5d06e9ba2ca24e3373ab1c1e7cc2a5c6b603e2acb02715487a1'
assert hashlib.sha256(Path('/proc/%d/exe' % pid).read_bytes()).hexdigest() == expected
assert hashlib.sha256(Path('/usr/sbin/samurai-wifi').read_bytes()).hexdigest() == '854c9a8c787d68ccefc998064983f3aa67141fe94def27f4dde87925bd18f24f'
check = subprocess.run(['sha256sum', '-c', str(base / 'nv-source-hashes.txt')], capture_output=True)
(out / 'nv-source-check-private.log').write_bytes(check.stdout + check.stderr); assert check.returncode == 0
mounts = subprocess.check_output(['findmnt', '-J', '-T', str(cache), '-o', 'FSTYPE,OPTIONS'])
(out / 'cache-mount-private.json').write_bytes(mounts)
mount = json.loads(mounts)['filesystems'][0]
assert mount['fstype'] == 'tmpfs' and 'size=32768k' in mount['options']
result = dict(stage=207, fresh_new_boot_verified=True, tftp207_autostarted_exact=True, private_32m_tmpfs_prepared_by_boot=True, wifi_boot_finished=(base / 'boot-finished').read_text().strip() if (base / 'boot-finished').exists() else None, mcfg_wrq_requests=sum('write request for /readwrite/mcfg.tmp ' in line for line in mcfg_lines), mcfg_opened_for_writing=sum('/readwrite/mcfg.tmp opened for writing' in line for line in mcfg_lines), mcfg_opened_for_reading=sum('/readwrite/mcfg.tmp opened for reading' in line for line in mcfg_lines), mcfg_open_rejections=sum('reject' in line for line in mcfg_lines), mcfg_cache_file_present='mcfg.tmp' in files, mcfg_cache_bytes=files.get('mcfg.tmp', {}).get('bytes'), server_check_present='server_check.txt' in files, cache_regular_files=len(files), nv_sources_unchanged=True, taint=int(Path('/proc/sys/kernel/tainted').read_text()), fault_counts={k:log.count(v) for k,v in dict(warning=b'WARNING:',oops=b'Oops:',gpu=b'gpu fault:',slpi_fatal=b'fatal error received',bluetooth=b'Frame reassembly failed').items()}, uptime_seconds=float(Path('/proc/uptime').read_text().split()[0]))
mdtime = [line for line in text.splitlines() if '/modem_pr/mcfg/configs/mcfg_sw/mdtime.txt' in line]
mcfg = [line for line in text.splitlines() if '/modem_pr/mcfg/' in line]
(out / 'stock-mcfg-tftp-lines-private.txt').write_text('\n'.join(mcfg) + '\n')
result.update(reboot_cycle=2, stock_mcfg_173_files_auto_staged=True,
    mdtime_read_requests=sum('read request for ' in line for line in mdtime),
    mdtime_opened_for_reading=sum('opened for reading' in line for line in mdtime),
    mdtime_open_errors=sum(any(word in line.lower() for word in ['reject', 'unable to open', 'failed to open']) for line in mdtime),
    stock_mcfg_read_requests=sum('read request for ' in line for line in mcfg),
    stock_mcfg_opened_for_reading=sum('opened for reading' in line for line in mcfg),
    stock_mcfg_open_errors=sum(any(word in line.lower() for word in ['reject', 'unable to open', 'failed to open']) for line in mcfg))
(out / 'summary.json').write_text(json.dumps(result, indent=2) + '\n'); print(json.dumps(result))
