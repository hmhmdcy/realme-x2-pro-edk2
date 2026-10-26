"""Replace only existing Image data extents in cached adopted506 FAT."""
from pathlib import Path
import hashlib, importlib.util, json, os, subprocess
HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('adopted506_fat_parser', HERE.parent / 'eud-route-pm-candidate/package-logdump.py')
p = importlib.util.module_from_spec(spec)
spec.loader.exec_module(p)
ROOT = Path('/mnt/e/edk2-samurai-out/charging-management-20261023')
OLD = ROOT / 'route-pm-image506-logdump-private-01/logdump-route506-private.img'
OUT = ROOT / 'tcpm-sink507-logdump-private-01'
sha = lambda raw: hashlib.sha256(raw).hexdigest()

def main():
    assert not OUT.exists() and not (HERE / 'logdump-package-result.json').exists()
    build = json.loads((HERE / 'image-build-result.json').read_bytes())
    assert build['passed'] and build['parent_inputs_unchanged']
    row = build['build']
    image = Path(row['Image_path']).read_bytes()
    assert sha(image) == row['Image_sha256'] and len(image) == row['Image_bytes']
    old = OLD.read_bytes()
    assert sha(old) == 'b29ea41a7a076555f5f6848c9f343dbd8fb0f9271adbd4d3acd4fff9d092b0ff'
    parsed = p.parse_fat(old)
    entry = parsed['files']['Image']
    assert entry['sha256'] == 'c03cf30de35a3a621dff2568805e098656d499de45d5ce9af39c802e74356c24'
    assert entry['size'] == len(image)
    new = bytearray(old)
    cursor = 0
    for cluster in entry['clusters']:
        at = parsed['data_at'] + (cluster - 2) * parsed['bps']
        chunk = image[cursor:cursor+parsed['bps']]
        new[at:at+len(chunk)] = chunk
        cursor += len(chunk)
    assert cursor == len(image)
    checked = p.parse_fat(new)
    assert checked['files']['Image']['content'] == image
    assert checked['files']['SAMURAI.DTB'] == parsed['files']['SAMURAI.DTB']
    OUT.mkdir()
    target = OUT / 'logdump-tcpm-sink507-private.img'
    with target.open('xb') as stream:
        stream.write(new); stream.flush(); os.fsync(stream.fileno())
    run = subprocess.run(['/usr/sbin/fsck.fat','-n',str(target)], capture_output=True)
    (OUT/'fsck.stdout').write_bytes(run.stdout)
    (OUT/'fsck.stderr').write_bytes(run.stderr)
    assert run.returncode == 0 and target.read_bytes() == new
    # The algorithm writes existing file extents only, keeping allocation, directory and slack.
    mask = bytearray(len(old))
    cursor = 0
    for cluster in entry['clusters']:
        at = parsed['data_at'] + (cluster-2)*parsed['bps']
        count = min(parsed['bps'],len(image)-cursor)
        mask[at:at+count] = b'\1'*count
        cursor += count
    assert all(mask[i] or old[i] == new[i] for i in range(len(old)))
    result = dict(passed=True, trial_only=True, installed=False, Image_sha256=sha(image),
                  candidate=dict(path=str(target),sha256=sha(new),bytes=len(new)),
                  rollback=dict(path=str(OLD),sha256=sha(old),bytes=len(old)),
                  only_existing_Image_file_bytes_changed=True, allocation_directory_and_slack_exact=True,
                  alternate_DTB_exact=True, fsck_readonly_passed=True)
    (HERE/'logdump-package-result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result))

if __name__ == '__main__':
    main()
