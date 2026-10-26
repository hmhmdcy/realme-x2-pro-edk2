"""Locate calibration/CCT/lux functions in the retained exact OEM algorithms."""
from pathlib import Path
import hashlib, json
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
template=(HERE.parent/'kernel320/locate-stock-lsc.py').read_text()
template=template.replace("P=Path('/mnt/e/edk2-samurai-out/kernel320')", "P=Path('/mnt/e/edk2-samurai-out/kernel328')")
template=template.replace('start=at+1\n  for section', "start=at+1\n  at=raw.rfind(b'\\0',0,at)+1\n  for section")
old="[b'FormatLSCData',b'FormatDataTypeByte',b'meshHWRollOffSize out of bound',b'Memory allocation for LSC failed']"
reports=[]
manifest=json.loads((P/'oem-stats-source.json').read_text())
for kind,filename,needles in [
 ('awb','com.qti.stats.awb.so',[b'SetCalibrationData',b'[OTP]:: goldenModuleCal rg, bg = (%d, %.4f, %.4f)',
 b'[OTP]:: MWB calibration',b'Different numbers of calibration factors (input = %d, tuning param = %d)',
 b'GetGainFromCCT',b'GetCCTFromGain']),
 ('aec','com.qti.stats.aec.so',[b'CalculateLuxIndex',b'EstimateLuxIndexForSlave'])]:
 path=P/'stats-source'/filename
 item=next(r for r in manifest['files'] if r['file']==filename)
 assert path.stat().st_size==item['bytes'] and hashlib.sha256(path.read_bytes()).hexdigest()==item['sha256']
 s=template.replace("path=P.parent/'kernel316/hal-source/camera.qcom.so'", "path=P/'stats-source'/"+repr(filename))
 s=s.replace(old,repr(needles)).replace('stock-lsc-',kind+'-functions-')
 exec(compile(s,str(HERE/'locate-algorithm-paths.py'),'exec'),{'__file__':str(HERE/'locate-algorithm-paths.py')})
 refs=json.loads((P/(kind+'-functions-xrefs.json')).read_text())
 reports.append(dict(component=kind,source=item,targets=refs))
report=dict(stage=328,components=reports,read_only_noload_noexec=manifest['read_only_noload_noexec'],
 unmounted=manifest['unmounted'],oem_code_executed=False,no_new_eeprom_reads=True,
 function_names_inferred_from_log_references_and_unwind=True,passed=True)
(HERE/'algorithm-source-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print('Saved exact OEM AWB/AEC source fingerprints and offline calibration/CCT/lux function locations.')
