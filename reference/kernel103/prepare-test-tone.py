from pathlib import Path
import hashlib, math, struct, wave
out=Path('/mnt/e/edk2-samurai-out/kernel103')
target=out/'tone-low-private.wav';assert not target.exists()
# 1kHz, two seconds, stereo S16_LE, peak 128/32768 (-48.16 dBFS).
data=bytearray()
for i in range(96000):
    envelope=min(1,i/2400,(96000-i-1)/2400)
    value=round(128*envelope*math.sin(2*math.pi*1000*i/48000))
    data.extend(struct.pack('<hh',value,value))
with wave.open(str(target),'wb') as w:
    w.setnchannels(2);w.setsampwidth(2);w.setframerate(48000);w.writeframes(data)
(out/'tone-sha-private.txt').write_text(hashlib.sha256(target.read_bytes()).hexdigest()+'\n')
print('BOUNDED_LOW_LEVEL_TEST_TONE_PREPARED')
