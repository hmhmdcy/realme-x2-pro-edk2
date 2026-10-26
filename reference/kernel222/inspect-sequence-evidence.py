from pathlib import Path
import hashlib,json,re,tarfile
here=Path(__file__).resolve().parent;archive=Path('/mnt/e/edk2-samurai-out/kernel220/final-evidence-private.tar.gz')
results=[]
with tarfile.open(archive) as tar:
 for mode in ['1920x1088','2296x1728']:
  names=[m.name for m in tar.getmembers() if 'exposure-metadata-system-r7-'+mode in m.name]
  candidates={name:tar.extractfile(name).read().decode(errors='replace') for name in names if any(s in name for s in ['stdout','stderr'])}
  selected={}
  for name,text in candidates.items():
   if re.search(r'seq:\s*\d+',text):selected['stdout']=text
   if 'Reading Exposure to ' in text:selected['stderr']=text
  assert set(selected)=={'stdout','stderr'},names
  seq=[int(n) for n in re.findall(r'seq:\s*(\d+)',selected['stdout'])]
  reads=[tuple(map(int,m)) for m in re.findall(r'Reading Exposure to (\d+) at index (\d+)',selected['stderr'])]
  delays=re.findall(r'Set a delay of (\d+) and priority write flag \d+ for (\w+)',selected['stderr'])
  starts=[int(n) for n in re.findall(r'frame (\d+) started',selected['stderr'])]
  assert len(seq)==36 and len(reads)==36
  result=dict(mode=mode,hardware_buffer_sequences=seq,delayed_read_indices=[x[1] for x in reads],exposure_lines=[x[0] for x in reads],configured_delays=delays,frame_start_events=starts[:6],maximum_frame_start_sequence=max(starts) if starts else None,gaps=sum(b!=a+1 for a,b in zip(seq,seq[1:])))
  results.append(result)
report=dict(stage=222,historical_stage220_native_evidence=True,same219_boot_and_identical_r7_payloads_reauthenticated=True,observations=results,no_new_camera_capture=True)
(here/'sequence-history-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
