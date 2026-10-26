from pathlib import Path
import hashlib, json, shutil
root=Path('/mnt/e/RealmeX2Pro edk2');ref=root/'reference/kernel104';old=root/'reference/kernel103'
out=Path('/mnt/e/edk2-samurai-out/kernel104');prev=out.parent/'kernel103'
for name, destination in [('collect-audio-runtime-retry1.sh','collect-audio-runtime.sh'),('test-playback.sh','test-playback.sh'),('test-auto-network.sh','test-auto-network.sh')]:
    assert not (ref/destination).exists()
    s=(old/name).read_text().replace('kernel103','kernel104').replace('k103','k104').replace('#102 SMP PREEMPT','#103 SMP PREEMPT')
    if destination=='collect-audio-runtime.sh':s=s.replace('audio-runtime-retry1','audio-runtime')
    (ref/destination).write_text(s)
copies=['tinymix','tinypcminfo','tinyplay','tinycap','tone-low-private.wav']
for n in copies:
    assert not (out/n).exists()
    shutil.copyfile(prev/n,out/n)
(out/'private-test-inputs.json').write_text(json.dumps({n:hashlib.sha256((out/n).read_bytes()).hexdigest() for n in copies},indent=2)+'\n')
print('FRESH_STAGE104_RUNTIME_NETWORK_AND_PLAYBACK_TOOLS_PREPARED')
