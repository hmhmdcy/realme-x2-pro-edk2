from pathlib import Path
import hashlib,json,struct,sys,zlib
repo=Path('/home/cy122/edk2-samurai/repo')
out=Path('/mnt/e/edk2-samurai-out/kernel126')
backup=out/'canonical-firmware-source-backup'
fv=repo/'workspace/Build/samurai/RELEASE_GCC5/FV'
checks=[(repo/'Platform/Realme/sm8150/FdtBlob/samurai/sm8150-realme-samurai.dtb',backup/'firmware-before.dtb'),
        (fv/'SM8150_UEFI.fd',backup/'firmware-before.fd'),(fv/'FVMAIN.Fv',backup/'fvmain-before.Fv'),
        (fv/'FVMAIN_COMPACT.Fv',backup/'fvcompact-before.Fv')]
assert all(a.read_bytes()==b.read_bytes() for a,b in checks)
old=(backup/'boot-before.img').read_bytes();new=(repo/'boot-samurai.img').read_bytes()
if '--allow-recompression' in sys.argv:
    def decode(boot):
        assert boot[:8]==b'ANDROID!'
        ks,rs,pg=[struct.unpack_from('<I',boot,o)[0] for o in (8,16,36)]
        assert pg==2048 and rs==1
        decoder=zlib.decompressobj(31)
        raw=decoder.decompress(boot[pg:pg+ks])+decoder.flush()
        assert decoder.eof and not decoder.unconsumed_tail
        align=lambda n:(n+pg-1)//pg*pg
        ramdisk=boot[pg+align(ks):pg+align(ks)+rs]
        header=bytearray(boot[:pg]);header[8:12]=b'\0'*4;header[576:608]=b'\0'*32
        return raw,decoder.unused_data,ramdisk,header
    assert decode(old)==decode(new), 'Original boot executable or header semantics changed'
    # gzip input timestamps can change. Preserve the exact original signed header/digest bytes.
    (repo/'boot-samurai.img').write_bytes(old)
assert (repo/'boot-samurai.img').read_bytes()==old
report=dict(original_source_dtb_restored=True,original_fd_fv_and_compact_restored=True,
            original_boot_byte_exact_restored=True,
            boot_sha256=hashlib.sha256(old).hexdigest(),original_source_preserved=True)
(out/'original-firmware-restore-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print('ORIGINAL_FIRMWARE_SOURCE_AND_ARTIFACTS_BYTE_EXACT_RESTORE_PASS')
