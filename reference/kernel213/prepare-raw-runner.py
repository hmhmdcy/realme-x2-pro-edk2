from pathlib import Path
here=Path(__file__).resolve().parent
text=(here/'run-pattern-probe.py').read_text()
text=text.replace("assert sys.argv[1:] in [['helper'],['lut']];variant=sys.argv[1]", "assert len(sys.argv)==4 and sys.argv[1] in ['helper','lut'] and sys.argv[2] in ['raw','rgb'] and sys.argv[3] in ['0','2'];variant=sys.argv[1];kind=sys.argv[2];pattern=int(sys.argv[3]);tag=variant+'-'+kind+'-p'+str(pattern)")
text=text.replace("'pattern-probe-build-validation.json'", "'raw-dark-probe-build-validation.json'").replace("['ambient_independent_sensor_color_bar_probe_built']", "['raw10_dark_statistics_probe_built']")
text=text.replace("variant=VARIANT;out=root/('k213-pattern-'+variant)", "variant=VARIANT;kind=KIND;pattern=PATTERN;tag=TAG;out=root/('k213-'+tag)")
text=text.replace("['/run/samurai-camera213-pattern-probe',node]", "['/run/samurai-camera213-raw-dark-probe',node,kind,str(pattern)]")
text=text.replace("sensor_internal_color_bars=True,ambient_independent=True", "requested_sensor_pattern=pattern,capture_kind=kind,test_pattern_effectiveness_not_assumed=True,all_active_raw10_pixels_examined=kind=='raw',raw_row_padding_excluded=kind=='raw',stream_geometry={k:data[k] for k in ['width','height','stride']} if data else {}")
text=text.replace("'''.replace('VARIANT',repr(variant))", "'''.replace('VARIANT',repr(variant)).replace('KIND',repr(kind)).replace('PATTERN',repr(pattern)).replace('TAG',repr(tag))")
text=text.replace("variant+'-pattern-probe-host-private.log'", "tag+'-probe-host-private.log'").replace("variant+'-pattern-probe-validation.json'", "tag+'-probe-validation.json'")
(here/'run-raw-dark-probe.py').write_text(text)
