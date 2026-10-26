#!/usr/bin/python3
"""Install the Samurai UCM overlay into an explicit live or staged rootfs."""
import argparse
import json
import os
from pathlib import Path
import shutil

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root',required=True)
    args = parser.parse_args()
    root = Path(args.root).resolve(strict=True)
    if not root.is_dir(): parser.error('Rootfs directory required')
    source = Path(__file__).resolve().parent.parent
    files = [('scripts/samurai-audio-route.py','usr/libexec/samurai-audio-route',0o755),
             ('ucm2/conf.d/Realme_X2_Pro/Realme_X2_Pro.conf','usr/share/alsa/ucm2/conf.d/Realme_X2_Pro/Realme_X2_Pro.conf',0o644),
             ('ucm2/conf.d/Realme_X2_Pro/HiFi.conf','usr/share/alsa/ucm2/conf.d/Realme_X2_Pro/HiFi.conf',0o644)]
    for src, name, mode in files:
        dest = root / name
        if not dest.resolve(strict=False).is_relative_to(root): raise RuntimeError('Rootfs path escaped')
        for directory in reversed([dest.parent] + list(dest.parent.parents)):
            if directory == root or not directory.is_relative_to(root): continue
            if not directory.exists():
                directory.mkdir(mode=0o755); directory.chmod(0o755)
        temporary = dest.with_name(dest.name+'.samurai-new')
        shutil.copyfile(source / src,temporary); os.chmod(temporary,mode); os.replace(temporary,dest)
    print(json.dumps(dict(installed=[name for src,name,mode in files],root=str(root))))

if __name__ == '__main__': main()
