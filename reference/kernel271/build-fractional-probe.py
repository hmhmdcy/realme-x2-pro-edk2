"""Compile fractional-gain validation and a longer automatic exposure observation."""
from pathlib import Path
R=Path(__file__).resolve().parent
text=(R/'build-control-probe.py').read_text()
for a,b in [
 ('[(2000,1), (8000,1), (32000,1), (32000,2), (32000,4), (32000,8), (32000,16), (32000,1)]','[(32000,1), (32000,1.03125), (32000,1.5), (32000,2), (32000,4), (32000,8), (32000,16), (32000,1)]'),
 ('{{{2000,1}, {8000,1}, {32000,1}, {32000,2}, {32000,4}, {32000,8}, {32000,16}, {32000,1}}}', '{{{32000,1}, {32000,1.03125}, {32000,1.5}, {32000,2}, {32000,4}, {32000,8}, {32000,16}, {32000,1}}}'),
 ('automaticMode ? 180 : 96', 'automaticMode ? 360 : 96'),('automatic_frames=180','automatic_frames=360'),
 ("source = R / 'telephoto-control-probe.cpp'", "source = R / 'telephoto-fractional-probe.cpp'"),
 ("name = 'telephoto-control-probe271'", "name = 'telephoto-fractional-probe271'"),
 ('control-probe-build-private.log','fractional-probe-build-private.log'),
 ('control-probe-build-validation.json','fractional-probe-build-validation.json'),
 ('integer real multipliers, baseline boot270 driver','native codes with real-gain helper, candidate r20 stack')
]:
    assert a in text,a
    text=text.replace(a,b)
exec(compile(text,'fractional-probe-build-generated.py','exec'),dict(__file__=str(R/'fractional-probe-build-generated.py')))
