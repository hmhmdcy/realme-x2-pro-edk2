"""Tiny generated inputs only; never uses the actual vendor member or plan."""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import unittest
import zipfile
import zlib

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('actual_extract', HERE / 'extract-vendor.py')
actual = importlib.util.module_from_spec(spec); spec.loader.exec_module(actual)
parser = argparse.ArgumentParser(); parser.add_argument('--private-output', required=True)
args = parser.parse_args(); OUT = Path(args.private_output); OUT.mkdir(mode=0o700)
NODE = r'C:\Program Files\nodejs\node.exe'
assert actual.digest(NODE) == actual.FACTS['node_sha256']
children = []; cases = []

def child(label, argv):
    with (OUT / (label + '.stdout-private.json')).open('xb') as out, (OUT / (label + '.stderr-private.log')).open('xb') as err:
        p = subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=out, stderr=err)
        try: pass
        finally: rc = p.wait()
    children.append({'label': label, 'pid': p.pid, 'terminal': True, 'returncode': rc})
    return rc, (OUT / (label + '.stdout-private.json')).read_bytes()

def transfer(text=None):
    return (text or '4\n4\n0\n0\nerase 2,0,1\nnew 2,1,3\nzero 2,3,4\nnew 2,4,5\n').encode()

class Small(unittest.TestCase):
    def test_transfer_exact_reconstruction(self):
        parsed = actual.parse_transfer(transfer(), 5 * 4096)
        data = b'A' * 4096 + b'B' * 4096 + b'C' * 4096
        source = OUT / 'valid.dat'; source.write_bytes(data); dest = OUT / 'valid.img'
        result = actual.rebuild_image(source, dest, parsed, hashlib.sha256(data).hexdigest())
        self.assertEqual(dest.read_bytes(), b'\0' * 4096 + data[:8192] + b'\0' * 4096 + data[8192:])
        self.assertEqual(result['new_bytes_consumed'], len(data)); self.assertTrue(result['EOF_checked'])
        cases.append('actual transfer parse/rebuild with erase/new/zero, complete coverage and EOF')

    def test_transfer_rejects_ranges(self):
        valid = transfer().decode()
        variants = {'overlap': valid.replace('zero 2,3,4', 'zero 2,2,4'),
                    'gap': valid.replace('new 2,1,3', 'new 2,2,3'),
                    'out-of-bounds': valid.replace('new 2,4,5', 'new 2,4,6'),
                    'unsupported': valid.replace('erase ', 'move ')}
        for label, text in variants.items():
            with self.subTest(label=label):
                with self.assertRaises(ValueError): actual.parse_transfer(text.encode(), 5 * 4096)
                cases.append('actual transfer rejects ' + label)

    def test_new_stream_short_extra_digest_and_exclusive(self):
        parsed = actual.parse_transfer(transfer(), 5 * 4096)
        for label, size in [('short', 3 * 4096 - 1), ('extra', 3 * 4096 + 1)]:
            source = OUT / (label + '.dat'); source.write_bytes(b'X' * size)
            dest = OUT / (label + '.img')
            with self.assertRaises(ValueError): actual.rebuild_image(source, dest, parsed, '0' * 64)
            self.assertFalse(dest.exists()); cases.append('actual rebuild rejects ' + label + ' new.dat before image')
        source = OUT / 'digest.dat'; source.write_bytes(b'X' * (3 * 4096)); dest = OUT / 'digest.img'
        with self.assertRaisesRegex(ValueError, 'digest'): actual.rebuild_image(source, dest, parsed, '0' * 64)
        self.assertTrue(dest.exists()); self.assertEqual(dest.stat().st_size, 5 * 4096)
        with self.assertRaises(FileExistsError): actual.rebuild_image(source, dest, parsed, actual.digest(source))
        cases.append('actual rebuild digest failure retains partial and refuses overwrite')

    def test_zip_crc_and_exclusive(self):
        data = b'fake vendor bytes' * 32; archive = OUT / 'small.zip'
        with zipfile.ZipFile(archive, 'x') as z: z.writestr('vendor.new.dat.br', data, compress_type=zipfile.ZIP_STORED)
        target = OUT / 'small.br'
        result = actual.copy_member(archive, 'vendor.new.dat.br', target, len(data), zlib.crc32(data))
        self.assertEqual(target.read_bytes(), data); self.assertTrue(result['EOF_and_ZIP_CRC_checked'])
        with self.assertRaises(FileExistsError): actual.copy_member(archive, 'vendor.new.dat.br', target, len(data), zlib.crc32(data))
        with zipfile.ZipFile(archive) as z:
            item = z.getinfo('vendor.new.dat.br'); offset = item.header_offset + 30 + len(item.filename.encode()) + len(item.extra)
        corrupt = bytearray(archive.read_bytes()); corrupt[offset] ^= 1
        bad = OUT / 'bad-crc.zip'; bad.write_bytes(corrupt)
        with self.assertRaises(zipfile.BadZipFile): actual.copy_member(bad, 'vendor.new.dat.br', OUT / 'bad-crc.br', len(data), zlib.crc32(data))
        cases.append('actual ZIP stream EOF/CRC and exclusive output; corrupted stored member rejected')

    def test_node_pipeline_valid_truncated_overflow_trailing(self):
        data = b'fixture only; no actual vendor payload\n' * 1024
        raw = OUT / 'node.dat'; raw.write_bytes(data); br = OUT / 'node.br'
        code = "const f=require('node:fs'),z=require('node:zlib');f.writeFileSync(process.argv[2],z.brotliCompressSync(f.readFileSync(process.argv[1])),{flag:'wx'})"
        rc, _ = child('compress-fixture', [NODE, '-e', code, str(raw), str(br)]); self.assertEqual(rc, 0)
        encoded = br.read_bytes()
        variants = [('valid', encoded, len(data)), ('truncated', encoded[:-1], len(data)),
                    ('overflow', encoded, len(data) - 1), ('trailing', encoded + b'TRAILING', len(data))]
        for label, compressed, expected in variants:
            with self.subTest(label=label):
                source = OUT / (label + '-node.br'); source.write_bytes(compressed)
                dest = OUT / (label + '-node.dat')
                rc, stdout = child(label, [NODE, str(HERE / 'brotli-stream.js'), str(source), str(dest),
                    str(len(compressed)), str(expected), hashlib.sha256(compressed).hexdigest()])
                result = json.loads(stdout)
                if label == 'valid':
                    self.assertEqual(rc, 0); self.assertTrue(result['passed'])
                    self.assertEqual(result['engine_bytes_written'], len(compressed)); self.assertEqual(dest.read_bytes(), data)
                else:
                    self.assertNotEqual(rc, 0); self.assertFalse(result['passed'])
                    self.assertLessEqual(dest.stat().st_size, expected)
                cases.append('actual Node pipeline ' + label)

suite = unittest.defaultTestLoader.loadTestsFromTestCase(Small)
with (OUT / 'unittest-private.log').open('w', encoding='utf-8') as log:
    outcome = unittest.TextTestRunner(stream=log, verbosity=2).run(suite)
result = {'passed': outcome.wasSuccessful(), 'actual_methods': outcome.testsRun, 'cases': cases,
          'children': children, 'fixture_only': True, 'actual_vendor_payload_read': False,
          'tested_files': {name: actual.digest(HERE / name) for name in ('extract-vendor.py', 'brotli-stream.js', 'test-small.py')},
          'private_output': str(OUT), 'private_log_sha256': actual.digest(OUT / 'unittest-private.log')}
actual.save(OUT / 'test-result-private.json', result)
actual.save(HERE / 'test-result.json', {key: value for key, value in result.items() if key != 'private_output'})
print(json.dumps(result)); raise SystemExit(0 if result['passed'] else 1)
