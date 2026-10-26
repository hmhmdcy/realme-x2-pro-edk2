import re
import tarfile
with tarfile.open('/mnt/e/edk2-samurai-out/kernel131/k131-native-fbo-comparison-private.tar.gz') as archive:
    for variant in ['control', 'fixed']:
        before = archive.extractfile('./' + variant + '/dmesg-before.txt').read().decode().splitlines()
        after = archive.extractfile('./' + variant + '/dmesg-delayed.txt').read().decode().splitlines()
        for line in after[len(before):]:
            if re.search(r'gpu.*fault|FAULT.*gpu|CCU.*TRANSLATION|CP.*FAULT', line, re.I):
                print(variant, re.sub(r'0x[0-9a-fA-F]+|[0-9a-fA-F]{8,}', '<address>', line))
