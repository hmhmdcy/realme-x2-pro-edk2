from pathlib import Path
import hashlib,json,shutil,subprocess
R=Path(__file__).parent;P=Path('/mnt/e/edk2-samurai-out/kernel263');SDK=Path('/home/cy122/x2pro-linux/libcamera214-root');W=SDK/'work/pipewire263-native-stream';assert not W.exists();W.mkdir()
shutil.copyfile(R/'native-stream-probe.c',W/'probe.c')
q=subprocess.run(['chroot',str(SDK),'gcc','-std=gnu11','-O2','-Wall','-Wextra','-I/work/pipewire262/sdk/usr/include/pipewire-0.3','-I/work/pipewire262/sdk/usr/include/spa-0.2','/work/pipewire263-native-stream/probe.c','/work/pipewire263-broadcast/build/src/pipewire/libpipewire-0.3.so.0.1609.0','-o','/work/pipewire263-native-stream/probe'],capture_output=True)
(P/'native-stream-build-private.log').write_bytes(q.stdout+q.stderr)
assert q.returncode==0,(q.stdout+q.stderr).decode(errors='replace')[-2500:]
shutil.copyfile(W/'probe',P/'native-stream-probe')
result=dict(compiled=True,sha256=hashlib.sha256((W/'probe').read_bytes()).hexdigest(),public_pw_stream_api=True)
(R/'native-stream-build-validation.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
