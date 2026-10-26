from pathlib import Path
import hashlib,json,sys,tarfile
out=Path('/mnt/e/edk2-samurai-out/kernel113')
ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel113')
number=int(sys.argv[1]); assert number in (6,7,8,9,10,11,12,13,14)
def read(path):
    with tarfile.open(path) as tar:
        data={m.name.removeprefix('./'):tar.extractfile(m).read() for m in tar if m.isfile()}
    for line in data['SHA256SUMS'].decode().splitlines():
        digest,name=line.split('  ',1)
        assert hashlib.sha256(data[name.removeprefix('./')]).hexdigest()==digest
    return data
path=out/f'audio-radio-quiesce-{number}.tar'
data=read(path); boot=read(out/f'reboot-audio-clean-{number}.tar')
assert data['boot-id-private.txt']==boot['boot-id-private.txt']
assert data['state.txt'].splitlines()[-1]==b'0'
assert data['pcm-idle.txt'].strip()==b'closed\nclosed'
assert data['amps.txt'].count(b'powered=0 muted=1')==2
assert data['adsp-final-state.txt'].strip()==b'offline'
assert data['nv-check.txt'].count(b': OK')==6 and data['source-check.txt'].count(b': OK')==4
report=dict(archive_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),normal_reboot_attempt=number,
    matches_current_boot_checkpoint=True,pcm_closed_and_amplifiers_muted=True,
    adsp_stopped=True,nv6_sources4_unchanged=True,taint=0,long_term_audio_fix_accepted=False)
if number==12:
    assert data['initial-adsp-stop-exit.txt'].strip()==b'143'
    assert data['adsp-stop.txt'].strip()==b'Terminated'
    # This interrupted read was empty because native stop removed the card.
    # Retain the artifact without inventing post-stop PCM measurements.
    assert data['pcm-idle-final.txt']==b''
    assert data['soundcards-after-stop.txt'].strip()==b'--- no soundcards ---'
    assert data['post-stop-audio-card-absent.txt'].strip()==b'CARD0_AND_PLAYBACK_CAPTURE_STATUS_NODES_ABSENT_AFTER_NATIVE_ADSP_STOP'
    assert data['remoteproc-final-state.txt'].splitlines()==[b'0 slpi offline',b'1 modem offline',b'2 adsp offline']
    assert data['sensor-power-final-state.txt'].strip()==b'vdd=0 vddio=0'
    assert data['amps-final.txt'].count(b'powered=0 muted=1')==2
    assert b'INDEPENDENT_RECHECK' in data['finalization.txt']
    report.update(initial_adsp_stop_exit=143,bounded_stop_was_interrupted=True,
        independent_final_offline_and_audio_state_recheck_pass=True,
        post_stop_sound_card_absent=True,post_stop_pcm_sample_not_available=True)
if number in (13,14):
    assert data['soundcards-after-stop.txt'].strip()==b'--- no soundcards ---'
    assert data['post-stop-audio-card-absent.txt'].strip()==b'CARD0_AND_PLAYBACK_CAPTURE_STATUS_NODES_ABSENT_AFTER_NATIVE_ADSP_STOP'
    assert data['remoteproc-final-state.txt'].splitlines()==[b'0 slpi offline',b'1 modem offline',b'2 adsp offline']
    assert data['sensor-power-final-state.txt'].strip()==b'vdd=0 vddio=0'
    assert data['amps-final.txt'].count(b'powered=0 muted=1')==2
    report.update(adsp_stop_bounded_deadline_seconds=25,
        all_dsp_offline_and_audio_state_recheck_pass=True,
        post_stop_sound_card_absent=True,post_stop_pcm_sample_not_available=True)
(ref/f'audio-quiesce-{number}-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
