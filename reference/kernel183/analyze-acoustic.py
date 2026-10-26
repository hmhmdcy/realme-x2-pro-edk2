from pathlib import Path
import hashlib, io, json, math, sys, tarfile, wave
import numpy as np

def analyze_samples(data,case,report):
    n=960;window=np.hanning(n);time_axis=np.arange(n)/48000
    frames=data[:len(data)//n*n].reshape(-1,n);frames=frames-frames.mean(axis=1,keepdims=True)
    kernel=window*np.exp(-2j*np.pi*case['frequency']*time_axis)
    amplitude=2*np.abs(frames@kernel)/window.sum();energy=amplitude**2
    template=np.repeat(report['code'],10).astype(np.float64)
    expected=case['play_start_after_capture_seconds']+report['leading_silence_seconds']
    start_min=max(25,int((expected-.5)/.02));start_max=min(len(energy)-len(template),int((expected+.8)/.02))
    correlations=[]
    for start in range(start_min,start_max+1):
        y=energy[start:start+len(template)]
        corr=float(np.corrcoef(template,y)[0,1]) if np.std(y)>0 else 0
        correlations.append((corr,start))
    corr,start=max(correlations)
    selected=energy[start:start+len(template)].reshape(15,10)[:,2:8]
    flags=np.array(report['code'],dtype=bool)
    on=float(selected[flags].mean());off=float(selected[~flags].mean())
    row=dict(case=case['case'],speaker=case['speaker'],frequency_hz=case['frequency'],
             target_speaker_enabled=case['target_speaker_enabled'],best_code_energy_correlation=corr,
             code_start_seconds=start*.02,expected_code_start_seconds=expected,
             code_on_band_rms_pcm_counts=math.sqrt(on/2),code_off_band_rms_pcm_counts=math.sqrt(off/2),
             on_to_off_band_power_db=10*math.log10(max(on,1e-12)/max(off,1e-12)),
             capture_rms_after_half_second=float(np.sqrt(np.mean(data[24000:]**2))),
             clipped_samples_after_half_second=int(np.count_nonzero(np.abs(data[24000:])>=32767)))
    return row,amplitude,on,off

archive=Path(sys.argv[1]);label=archive.name.removesuffix('-private.tar.gz').removeprefix('k183-')
out=archive.parent;ref=Path(__file__).resolve().parent
with tarfile.open(archive) as t:
    prefix='k183-'+label+'/'
    report=json.loads(t.extractfile(prefix+'capture-validation.json').read())
    rows=[];features={};pair={}
    for case in report['cases']:
        with wave.open(io.BytesIO(t.extractfile(prefix+case['case']+'-capture-private.wav').read()),'rb') as w:
            assert (w.getnchannels(),w.getsampwidth(),w.getframerate())==(1,2,48000)
            data=np.frombuffer(w.readframes(w.getnframes()),dtype='<i2').astype(np.float64)
        row,amplitude,on,off=analyze_samples(data,case,report)
        rows.append(row);features[case['case']]=amplitude.tolist()
        pair[(case['speaker'],case['target_speaker_enabled'])]=(row,on,off)
    decisions=[]
    for speaker in ['left','right']:
        pos,p_on,p_off=pair[(speaker,True)];neg,n_on,n_off=pair[(speaker,False)]
        on_to_disabled=10*math.log10(max(p_on,1e-12)/max(n_on,1e-12))
        detected=pos['best_code_energy_correlation']>=.75 and pos['on_to_off_band_power_db']>=6 and on_to_disabled>=8
        decisions.append(dict(speaker=speaker,known_tone_detected_with_disabled_amp_control=detected,
                              active_code_correlation=pos['best_code_energy_correlation'],
                              disabled_code_correlation=neg['best_code_energy_correlation'],
                              active_on_to_off_db=pos['on_to_off_band_power_db'],
                              active_to_disabled_tone_band_db=on_to_disabled))
summary=dict(stage=183,kernel_build=183,capture_input=report['cases'][0]['capture_input'],tone_peak_dbfs=report['tone_peak_dbfs'],
             method='20ms Hann coherent tone-band energy; coded 15-slot envelope; physical target amp-off control',
             correlation_search_accounts_for_pcm_start_latency=True,
             threshold_predeclared_correlation=.75,threshold_predeclared_on_off_db=6,threshold_predeclared_amp_control_db=8,
             results=rows,speaker_decisions=decisions,taint=report['taint'],fault_delta=report['fault_delta'],
             mixer_restored=report['mixer_restored'],amplifiers_off=report['all_final_amplifiers_off'],
             archive_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),
             physical_listening_quality_and_calibrated_frequency_response_not_verified=True)
(out/(label+'-features-private.json')).write_text(json.dumps(features)+'\n')
(out/(label+'-analysis.json')).write_text(json.dumps(summary,indent=2)+'\n')
(ref/(label+'-analysis.json')).write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps(summary,indent=2))
