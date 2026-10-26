from pathlib import Path
import host

source=(Path(__file__).resolve().parent.parent/'kernel185/collect-reboot-runtime.py').read_text()
source=source.replace('/var/lib/samurai/k185-reboot-runtime','/var/lib/samurai/k186-reboot-runtime-r2')
source=source.replace('/var/lib/samurai/k185-preflash','/var/lib/samurai/k186r2-preflash')
source=source.replace("'stage': 185","'stage': 186")
marker="(out / 'summary.json').write_text(json.dumps(report, indent=2) + '\\n')"
extra='''fastrpc = module_root / 'kernel/drivers/misc/fastrpc.ko'
assert hashlib.sha256(fastrpc.read_bytes()).hexdigest() == '4515b1b22f212ce2ec482039343d9b72193ef2100e8b0b97227bdde2f37156aa'
fastrpc_loaded = Path('/sys/module/fastrpc').exists()
if fastrpc_loaded:
    elf = fastrpc.read_bytes()
    offset = struct.unpack_from('<Q',elf,40)[0]
    size, count, names = struct.unpack_from('<HHH',elf,58)
    entries = [struct.unpack_from('<IIQQQQIIQQ',elf,offset+i*size) for i in range(count)]
    table = elf[entries[names][4]:entries[names][4]+entries[names][5]]
    item = next(e for e in entries if table[e[0]:].split(b'\\0',1)[0] == b'.note.gnu.build-id')
    assert Path('/sys/module/fastrpc/notes/.note.gnu.build-id').read_bytes() == elf[item[4]:item[4]+item[5]]
report['original_fastrpc_default_file_restored'] = True
report['original_fastrpc_loaded_and_verified'] = fastrpc_loaded
report['failed_candidate_not_loaded'] = True
report['current_slpi_not_started'] = True
'''
assert source.count(marker)==1
source=source.replace(marker,extra+marker)
p=host.ssh('python3 -',input=source.encode(),timeout=55)
(host.PRIVATE/'runtime-r2-host-private.log').write_bytes(p.stdout+p.stderr)
print(p.stdout.decode().strip())
