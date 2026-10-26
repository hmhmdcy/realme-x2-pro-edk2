from pathlib import Path
import hashlib, json, mmap, os, re, struct

os.umask(0o077)
assert os.uname().version.startswith('#163 ')
out = Path('/var/lib/samurai/k165-firmware-log-mmap')
assert not out.exists()
out.mkdir(mode=0o700)
(out / 'boot-id-private.txt').write_bytes(Path('/proc/sys/kernel/random/boot_id').read_bytes())
report = dict(stage=165, kernel_build=163, read_only=True, physical_log_address=0x9ffe3000,
              bytes_requested=0x14000, marker_observed=False, callback_success_observed=False)
try:
    fd = os.open('/dev/mem', os.O_RDONLY | os.O_CLOEXEC)
    try:
        with mmap.mmap(fd, 0x14000, flags=mmap.MAP_SHARED, prot=mmap.PROT_READ, offset=0x9ffe3000) as mapped:
            raw = mapped[:]
    finally:
        os.close(fd)
    assert len(raw) == 0x14000
    magic, version, size, head, tail, drops, drop_events, pad = struct.unpack_from('<8I', raw)
    assert magic == 0x474f4c45 and version == 0x10000 and size == len(raw)-32
    body = raw[32:]
    text = bytes(body[index % size] for index in range(max(0, head-size), head)).decode(errors='replace')
    (out / 'raw-ring-private.bin').write_bytes(raw)
    (out / 'retained-log-private.txt').write_text(text)
    markers = re.findall(r'\[SAMURAI\] panel reset before Linux ExitBootServices:\s*([^\r\n]+)', text)
    report.update(header_valid=True, ring_drops=drops, ring_drop_events=drop_events,
                  marker_observed=bool(markers), callback_statuses=markers,
                  callback_success_observed=bool(markers) and all(value.strip().lower() == 'success' for value in markers),
                  raw_ring_sha256=hashlib.sha256(raw).hexdigest())
except (OSError, AssertionError) as error:
    report.update(read_error=type(error).__name__ + ': ' + str(error))
(out / 'result.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report))

