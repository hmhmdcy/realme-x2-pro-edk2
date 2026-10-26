"""Apply only the parameterized diagnostic; retain the proven SoC core."""
from pathlib import Path
HERE=Path(__file__).resolve().parent
s=(HERE.parent/'kernel384/apply-source.py').read_text()
s=s.replace("['serializer','transfer']","['diagnostic']")
s=s.replace('samurai-a5-ipe-native384','samurai-a5-ipe-frames385')
s=s.replace('media: camss: serialize native bypass pass and stripe geometry','media: camss: exercise variable IPE frames through alternating sessions')
s=s.replace("HERE.parent/'kernel383/build-intree.py'","HERE.parent/'kernel384/build-intree.py'")
s=s.replace("replace('stage=383','stage=384')","replace('stage=384','stage=385')")
s=s.replace("P.parent/'kernel383'","P.parent/'kernel384'")
exec(compile(s,str(HERE/'apply-source-generated.py'),'exec'),globals())
