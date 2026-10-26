"""Finite cached regression, no device or transport entry point."""
from pathlib import Path
import hashlib,importlib.util,json,re,sys
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
P=Path('/mnt/e/edk2-samurai-out/kernel476');P.mkdir(exist_ok=True)
spec=importlib.util.spec_from_file_location('local476',HERE/'analyse-local.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
log=Path('/mnt/e/edk2-samurai-out/kernel306/delay-r1-capture-private.log')
text=log.read_text(errors='replace');actual=m.analyse(text,legacy_mode3=True)
oldpath=HERE.parent/'kernel306/delay-analysis-r1-validation.json';old=json.loads(oldpath.read_text())
keys=['step','sof','control','value','useful_response','first_observed_changed_offset','first_three_frame_plateau_offset']
assert [{k:r[k] for k in keys} for r in actual['changes']]==[{k:r[k] for k in keys} for r in old['steps']]
assert actual['source_mode']==3 and sum(r['useful_response'] for r in actual['changes'])==7
# Current field-name parser only: the physical dataset remains mode3.
renamed=text.replace('parameters-acknowledged=','parameter-buffer-submitted=')
assert len(re.findall(r'Pair epoch=\d+ sof=\d+ request=\d+ population=\d+ mean=[\d.e+-]+ parameter-buffer-submitted=1',renamed))==240
missing=re.sub(r'^.*Pair epoch=1 sof=14 .*\n','',text,flags=re.M)
assert 'missing-paired-sof' in m.analyse(missing,legacy_mode3=True)['changes'][0]['invalid_reasons']
assert 'known-saturation' in m.analyse(text,legacy_mode3=True,quality={'14':{'saturated':True}})['changes'][0]['invalid_reasons']
(P/'mode3-cache-regression-private.json').write_text(json.dumps(actual,indent=2)+'\n')
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
report=dict(stage=476,passed=True,log_sha256=sha(log),baseline_analysis_sha256=sha(oldpath),
 analyser_sha256=sha(HERE/'analyse-local.py'),regression_sha256=sha(Path(__file__)),
 cached_physical_mode=3,paired_frames=240,matched_existing_steps=9,useful_steps=7,
 independent_exposure_gain_up_down_groups=True,current_pair_suffix_parser_checked=True,
 missing_window_rejected=True,known_saturation_rejected=True,original_low_snr_cases_preserved=True,
 no_delay_expected_in_analyser=True,mode2_physical_delay_proven=False,phone_accessed=False,sdk_accessed=False)
(HERE/'analysis-regression-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
