from pathlib import Path
import array, json, math, os, re, subprocess, tarfile, time, wave

os.umask(0o077)
out=Path('/var/lib/samurai/k168-first-audio')
boot=(out/'boot-id-private.txt').read_bytes()
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==boot
assert Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
saved=json.loads((out/'mixer-before-private.json').read_text())
for name,value in saved.items():
    text=subprocess.check_output(['amixer','-c','0','cget',"name='"+name+"'"],text=True)
    assert re.search(r': values=(.*)',text)[1].strip()==value,name
plays=[];captures=[]
for i in range(3):
    live=(out/('play-'+str(i)+'-live-private.txt')).read_text()
    idle=(out/('play-'+str(i)+'-closed-private.txt')).read_text()
    assert 'RUNNING' in live and live.count('powered=1 muted=0')==2
    assert idle.count('powered=0 muted=1')==2
    plays.append(dict(index=i,returncode=0,pcm_live_running=True,both_amplifiers_on_then_off=True))
for dmic,dec in [('DMIC0',5),('DMIC1',7),('DMIC2',5)]:
    with wave.open(str(out/(dmic+'-private.wav')),'rb') as w:
        assert (w.getnchannels(),w.getsampwidth(),w.getframerate())==(1,2,48000)
        samples=array.array('h',w.readframes(w.getnframes()))
    tail=samples[24000:];assert len(samples)==144000 and any(tail)
    assert 'RUNNING' in (out/(dmic+'-live-private.txt')).read_text()
    captures.append(dict(input=dmic,dec=dec,frames=len(samples),nonzero_after_half_second=sum(x!=0 for x in tail),
                         clipped_after_half_second=sum(abs(x)>=32767 for x in tail),
                         rms_after_half_second=math.sqrt(sum(x*x for x in tail)/len(tail)),returncode=0))
with wave.open(str(out/'tone-low-private.wav'),'rb') as w: frames=w.readframes(w.getnframes())
cmd='XDG_RUNTIME_DIR=/run/user/10000 paplay --device=alsa_output.platform-sound.HiFi__Speaker__sink --volume=16384 --raw --format=s16le --rate=48000 --channels=2'
p=subprocess.run(['su','-s','/bin/sh','cy122','-c',cmd],input=frames,capture_output=True)
(out/'desktop-pipe-stderr-private.txt').write_bytes(p.stderr)
assert p.returncode==0,p.stderr
time.sleep(7)
amp=''.join(Path('/sys/bus/i2c/devices/'+name+'/status').read_text() for name in ['1-0039','1-003a'])
assert amp.count('powered=0 muted=1')==2
log=subprocess.check_output(['dmesg'],text=True);(out/'dmesg-final-private.txt').write_text(log)
patterns={'warnings':'WARNING:','prepare':'unable to prepare channel','tx_timeout':'TX timed out',
          'queue_full':'Message buffer unavailable','resume_failure':'NGD resume failed'}
counts={name:log.count(pattern) for name,pattern in patterns.items()}
report=dict(stage=168,kernel_build=168,native_playback=plays,digital_microphones=captures,
            desktop_playback_returncode=0,mixer_restored_before_desktop=True,final_amplifiers_off=True,
            taint=int(Path('/proc/sys/kernel/tainted').read_text()),faults_whole_boot=counts,
            same_boot=Path('/proc/sys/kernel/random/boot_id').read_bytes()==boot,tone_peak_dbfs=-48,
            initial_desktop_test_permission_error_preserved=True,desktop_test_fixed_with_stdin_pipe=True,
            physical_sound_and_pickup_quality_confirmed=False)
(out/'validation.json').write_text(json.dumps(report,indent=2)+'\n')
with tarfile.open('/tmp/k168-first-audio-private.tar.gz','w:gz') as archive: archive.add(out,arcname=out.name)
print(json.dumps(report),flush=True)
assert all(x==0 for x in counts.values()) and report['same_boot']
