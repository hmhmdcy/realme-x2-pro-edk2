"""Only a fixed vendor member -> bounded Brotli -> new host raw image.

Default checks small metadata/transfer and tool pins. Actual payload requires
--execute. The source ZIP location is supplied only by a private plan.
"""
from pathlib import Path
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import traceback
import zipfile
import zlib

HERE = Path(__file__).resolve().parent
CHUNK = 1024 * 1024
BLOCK = 4096
FACTS = {
    'source_bytes': 3666753073, 'member_count': 72,
    'metadata_sha256': '3e005ffe4beaf27b2611052d9000ed2d700ded5607433e04c44bd987be8953c0',
    'transfer_sha256': 'fedaa4798489600aac76c03f59b7b47c1e8eabca49a7ff9d11f9b1889382830f',
    'compressed_bytes': 699830594, 'compressed_crc32': '43496d61',
    'new_bytes': 1613049856, 'extent_bytes': 1711276032,
    'commands': {'erase': 1, 'new': 385, 'zero': 8},
    'node_sha256': 'd702daa815eabbff763c7d3808e235cf031cf2ca70211b56847bc72f51e240e5'
}

def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        while data := f.read(CHUNK): h.update(data)
    return h.hexdigest()

def save(path, value):
    with Path(path).open('w', encoding='utf-8', newline='\n') as f:
        json.dump(value, f, indent=2); f.write('\n'); f.flush(); os.fsync(f.fileno())

def stamp(path):
    s = Path(path).stat()
    return {'bytes': s.st_size, 'mtime_ns': s.st_mtime_ns, 'dev': s.st_dev, 'ino': s.st_ino}

def parse_transfer(raw, extent_bytes):
    if len(raw) > 65536 or extent_bytes <= 0 or extent_bytes % BLOCK:
        raise ValueError('bounded transfer/extent required')
    lines = raw.decode('ascii').splitlines()
    if len(lines) < 5 or lines[0] != '4' or lines[2:4] != ['0', '0']:
        raise ValueError('only fixed v4 without stash supported')
    total = int(lines[1]); commands = []; spans = []; blocks = {}; counts = {}
    for line in lines[4:]:
        words = line.split()
        if len(words) != 2 or words[0] not in ('new', 'zero', 'erase'):
            raise ValueError('unsupported command')
        kind = words[0]; values = list(map(int, words[1].split(',')))
        if not values or values[0] <= 0 or values[0] != len(values) - 1 or values[0] % 2:
            raise ValueError('invalid range count')
        ranges = list(zip(values[1::2], values[2::2]))
        for lo, hi in ranges:
            if not 0 <= lo < hi <= extent_bytes // BLOCK: raise ValueError('range outside exact extent')
            spans.append((lo, hi)); blocks[kind] = blocks.get(kind, 0) + hi - lo
        counts[kind] = counts.get(kind, 0) + 1; commands.append((kind, ranges))
    end = 0
    for lo, hi in sorted(spans):
        if lo != end: raise ValueError('overlap or gap in complete target coverage')
        end = hi
    if end * BLOCK != extent_bytes or total != blocks.get('new', 0) + blocks.get('zero', 0):
        raise ValueError('extent/header coverage mismatch')
    return {'commands': commands, 'counts': counts, 'blocks': blocks,
            'new_bytes': blocks.get('new', 0) * BLOCK, 'extent_bytes': extent_bytes,
            'header_new_plus_zero_blocks': total, 'complete_target_coverage': True}

def inspect_zip(path):
    if Path(path).stat().st_size != FACTS['source_bytes']: raise ValueError('source size mismatch')
    with zipfile.ZipFile(path) as z:
        infos = z.infolist(); names = [i.filename for i in infos]
        if len(infos) != FACTS['member_count'] or len(names) != len(set(names)):
            raise ValueError('member count or duplicate name')
        info = z.getinfo('vendor.new.dat.br')
        if (info.file_size, info.compress_size, info.compress_type, info.CRC, info.flag_bits) != (
                FACTS['compressed_bytes'], FACTS['compressed_bytes'], zipfile.ZIP_STORED,
                int(FACTS['compressed_crc32'], 16), 2048): raise ValueError('vendor member mismatch')
        for name, key, limit in [('META-INF/com/android/metadata', 'metadata_sha256', 4096),
                                 ('vendor.transfer.list', 'transfer_sha256', 65536)]:
            if z.getinfo(name).file_size > limit: raise ValueError('small member exceeds bound')
            data = z.read(name)
            if hashlib.sha256(data).hexdigest() != FACTS[key]: raise ValueError('small member mismatch')
            if name == 'vendor.transfer.list': transfer = data
    parsed = parse_transfer(transfer, FACTS['extent_bytes'])
    if parsed['counts'] != FACTS['commands'] or parsed['new_bytes'] != FACTS['new_bytes']:
        raise ValueError('fixed transfer arithmetic mismatch')
    return transfer, parsed

def copy_member(archive, member, target, expected_bytes, expected_crc):
    count = 0; crc = 0; h = hashlib.sha256()
    # Reading to EOF also invokes ZipExtFile's own CRC check.
    with zipfile.ZipFile(archive) as z, z.open(member) as source, Path(target).open('xb') as out:
        while data := source.read(CHUNK):
            count += len(data)
            if count > expected_bytes: raise ValueError('member exceeds bound')
            crc = zlib.crc32(data, crc); h.update(data); out.write(data)
        if count != expected_bytes or crc != expected_crc: raise ValueError('member length/CRC mismatch')
        out.flush(); os.fsync(out.fileno())
    return {'bytes': count, 'sha256': h.hexdigest(), 'crc32': f'{crc:08x}', 'EOF_and_ZIP_CRC_checked': True}

def rebuild_image(data_path, image_path, parsed, expected_sha):
    if Path(data_path).stat().st_size != parsed['new_bytes']: raise ValueError('new.dat size mismatch')
    before = stamp(data_path); h = hashlib.sha256(); consumed = 0
    with Path(data_path).open('rb') as source, Path(image_path).open('xb') as image:
        image.truncate(parsed['extent_bytes'])
        for kind, ranges in parsed['commands']:
            if kind != 'new': continue  # New host file only: zero/erase ranges remain zero.
            for lo, hi in ranges:
                image.seek(lo * BLOCK); remaining = (hi - lo) * BLOCK
                while remaining:
                    data = source.read(min(CHUNK, remaining))
                    if not data: raise ValueError('new.dat short read')
                    h.update(data); consumed += len(data); image.write(data); remaining -= len(data)
        if source.read(1) or consumed != parsed['new_bytes']: raise ValueError('new.dat trailing or incomplete consumption')
        if h.hexdigest() != expected_sha: raise ValueError('new.dat consumed digest mismatch')
        image.flush(); os.fsync(image.fileno())
    if before != stamp(data_path): raise ValueError('new.dat changed during reconstruction')
    return {'bytes': Path(image_path).stat().st_size, 'sha256': digest(image_path),
            'new_bytes_consumed': consumed, 'new_sha256': h.hexdigest(), 'EOF_checked': True,
            'zero_erase_are_new_host_file_unwritten_ranges_only': True}

def load_plan(path):
    p = json.loads(Path(path).read_bytes())
    if p['schema'] != 'samurai-gauge-vendor-only-extract-plan-v1': raise ValueError('plan schema')
    for key in ('source_zip', 'output_directory', 'node'):
        if not Path(p[key]).is_absolute(): raise ValueError('absolute private paths required')
    if p['expected'] != FACTS: raise ValueError('fixed facts mismatch')
    if digest(p['node']) != FACTS['node_sha256']: raise ValueError('Node executable mismatch')
    if digest(HERE / 'brotli-stream.js') != p['brotli_script_sha256']: raise ValueError('Node source mismatch')
    if digest(Path(__file__)) != p['extract_script_sha256']: raise ValueError('Python source mismatch')
    if Path(p['output_directory']).exists(): raise ValueError('unique output exists; no replay')
    return p

def node_decode(plan, outdir, compressed, result):
    command = [plan['node'], str(HERE / 'brotli-stream.js'), str(outdir / 'vendor.new.dat.br'),
               str(outdir / 'vendor.new.dat'), str(FACTS['compressed_bytes']),
               str(FACTS['new_bytes']), compressed['sha256']]
    entry = {'argv': command, 'terminal': False}; result['node_command'] = entry
    with (outdir / 'node-stdout-private.json').open('xb') as out, (outdir / 'node-stderr-private.log').open('xb') as err:
        child = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=out, stderr=err)
        try:
            entry['pid'] = child.pid; save(outdir / 'result-private.json', result)
            print(json.dumps({'stage': 'brotli', 'pid': child.pid}), flush=True)
        finally:
            entry['returncode'] = child.wait(); entry['terminal'] = True
        out.flush(); os.fsync(out.fileno()); err.flush(); os.fsync(err.fileno())
    if entry['returncode'] != 0: raise RuntimeError('original Node child failed; preserve outputs')
    decoded = json.loads((outdir / 'node-stdout-private.json').read_bytes())
    if not decoded['passed'] or not decoded['input_complete'] or decoded['input_sha256'] != compressed['sha256']:
        raise ValueError('Node receipt mismatch')
    if decoded['input_bytes'] != FACTS['compressed_bytes'] or decoded['engine_bytes_written'] != FACTS['compressed_bytes']:
        raise ValueError('Node engine input consumption mismatch')
    if decoded['output_file_bytes'] != FACTS['new_bytes'] or decoded['output_forwarded_bytes'] != FACTS['new_bytes']:
        raise ValueError('Node decoded length mismatch')
    return decoded

def execute(plan_path):
    plan = load_plan(plan_path); source = Path(plan['source_zip']); outdir = Path(plan['output_directory'])
    transfer, parsed = inspect_zip(source); before = stamp(source)
    # New outputs need ~4.03GB logically; require a conservative 5GB headroom.
    if shutil.disk_usage(outdir.parent).free < 5 * 1024**3: raise ValueError('insufficient private disk headroom')
    outdir.mkdir(mode=0o700)  # Exclusive: every error retains this directory and forbids replay.
    result = {'passed': False, 'pid': os.getpid(), 'scope': 'new host vendor-only artifacts; no device',
              'plan_sha256': digest(plan_path), 'source_before': before, 'small_members_rechecked': False}
    try:
        save(outdir / 'plan-private.json', plan)
        with (outdir / 'vendor.transfer.list').open('xb') as f: f.write(transfer); f.flush(); os.fsync(f.fileno())
        save(outdir / 'result-private.json', result)
        result['compressed'] = copy_member(source, 'vendor.new.dat.br', outdir / 'vendor.new.dat.br',
                                             FACTS['compressed_bytes'], int(FACTS['compressed_crc32'], 16))
        save(outdir / 'result-private.json', result)
        result['decoded'] = node_decode(plan, outdir, result['compressed'], result)
        result['image'] = rebuild_image(outdir / 'vendor.new.dat', outdir / 'vendor.img', parsed,
                                         result['decoded']['output_sha256'])
        inspect_zip(source)
        result['small_members_rechecked'] = True
        result['passed'] = True
    except BaseException as error:
        result['passed'] = False; result['error'] = repr(error); result['traceback'] = traceback.format_exc()
    finally:
        result['source_after'] = stamp(source)
        result['source_stat_unchanged'] = before == result['source_after']
        result['source_stat_and_small_members_unchanged'] = result['source_stat_unchanged'] and result['small_members_rechecked']
        result['tools_and_sources_unchanged'] = (digest(plan_path) == result['plan_sha256']
            and digest(plan['node']) == FACTS['node_sha256']
            and digest(HERE / 'brotli-stream.js') == plan['brotli_script_sha256']
            and digest(Path(__file__)) == plan['extract_script_sha256'])
        result['passed'] &= result['source_stat_and_small_members_unchanged']
        result['passed'] &= result['tools_and_sources_unchanged']
        result['source_whole_file_sha256_verified'] = False
        save(outdir / 'result-private.json', result)
        print(json.dumps({'passed': result['passed'], 'result_sha256': digest(outdir / 'result-private.json'),
                          'result_path': str(outdir / 'result-private.json')}), flush=True)
    return 0 if result['passed'] else 1

def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--plan', required=True); parser.add_argument('--execute', action='store_true')
    args = parser.parse_args()
    if args.execute: return execute(args.plan)
    plan = load_plan(args.plan); _, parsed = inspect_zip(plan['source_zip'])
    print(json.dumps({'checked': True, 'payload_read': False, 'output_created': False,
                      'complete_target_coverage': parsed['complete_target_coverage'], 'new_bytes': parsed['new_bytes'],
                      'extent_bytes': parsed['extent_bytes']}))
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
