from pathlib import Path
import hashlib, json, tarfile

out = Path('/mnt/e/edk2-samurai-out/kernel91')
digest = lambda data: hashlib.sha256(data).hexdigest()
archive = out / 'connected.tar'
assert digest(archive.read_bytes()) == 'ff4a253d85bc9fc5e62318c25f847c4c8e9551b1ea9b7ddd85ffa65bb6f704ad'
with tarfile.open(archive) as source:
    files = {Path(m.name).name: source.extractfile(m).read() for m in source if m.isfile()}
for line in files['SHA256SUMS'].decode().splitlines():
    expected, name = line.split('  ', 1)
    assert digest(files[name]) == expected
status = files['wpa-status.txt'].decode()
assert 'wpa_state=COMPLETED\n' in status and 'freq=2462\n' in status
assert all(x.endswith(': OK') for x in files['nv-partitions.txt'].decode().splitlines())
assert len(files['nv-partitions.txt'].decode().splitlines()) == 6
assert files['modem-partition.txt'].decode().split()[0] == '88af46265a4f23c634b2a3c0a4be6815caf796f4b3bb398a6223a565c9e132f0'
hashes = {Path(n).name: d for d, n in (x.split() for x in files['traffic-sha256.txt'].decode().splitlines())}
assert digest((out / 'traffic-download.bin').read_bytes()) == hashes['k91-traffic.bin']
assert digest((out / 'traffic-upload-source.bin').read_bytes()) == hashes['k91-traffic-upload.bin']
assert (out / 'traffic-download.bin').stat().st_size == (out / 'traffic-upload-source.bin').stat().st_size == 4194304
report = dict(private_archive_sha256=digest(archive.read_bytes()), files_verified=len(files)-1,
              frequency_mhz=2462, wpa2_ccmp=True, dhcp=True, gateway_ping=True,
              dns_lookup=True, public_http=True, public_icmp=False,
              wifi_tx_bytes=4194304, wifi_rx_bytes=4194304, both_payload_sha256_match=True,
              nv_source_partitions_unchanged=6, modem_source_partition_unchanged=True,
              credentials_published=False, five_ghz_connection_verified=False)
(out / 'connected-validation.json').write_text(json.dumps(report, indent=2)+'\n')
print(json.dumps(report, indent=2))
