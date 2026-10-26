from pathlib import Path
R=Path(__file__).resolve().parent
s=(R.parent/'kernel244/remove-boot-hook.py').read_text().replace('k244-runtime','k246-runtime').replace('k244-nextboot','k246-nextboot').replace('samurai-diag244','samurai-diag246').replace('stage=244','stage=246');compile(s,'remove-boot-hook.py','exec');(R/'remove-boot-hook.py').write_text(s);print('Prepared removal of owned246 startup hook after terminal state.')
