"""Inspect actual Gamma resource creation, not an assumed DMI buffer enum."""
from pathlib import Path
import importlib.util,json,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
hal=P.parent/'kernel281/camera.qcom.so-private'
q=subprocess.run(['aarch64-linux-gnu-objdump','-d','--start-address=0x355cb0','--stop-address=0x356180',str(hal)],capture_output=True,check=True);(P/'gamma-resource-private.asm').write_bytes(q.stdout)
repo='/home/cy122/x2pro-linux/refs/CamxChi-k117';rev='9f17f1b568626b393e785b369c5dc94543774d7a'
for rel in ['camx/src/core/camxcmdbuffer.h','camx/src/core/camxcmdbuffer.cpp']:
 (P/Path(rel).name).write_bytes(subprocess.check_output(['git','-C',repo,'show',rev+':'+rel]))
print('Saved original Gamma resource creation disassembly and bounded command-buffer sources privately.')
