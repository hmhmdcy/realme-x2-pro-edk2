"""Reuse the original PHY single-object builder in a distinct private view."""
from pathlib import Path
import ast,hashlib,json
HERE=Path(__file__).resolve().parent;OLD=HERE.parent/'apsd-phy-window-candidate'
original=(OLD/'build-private.py').read_text()
assert hashlib.sha256((OLD/'phy-qcom-snps-femto-v2.c').read_bytes()).hexdigest()=='cc8e7f3292792f1f921db090384202fcf8ebb426f5a782f976b5f4614ba6b6dc'
source=original.replace("/apsd-phy-window-candidate'","/apsd-phy-withdrawal-candidate'")
assert source!=original and source.count("'W=1','-j4'")==1
source=source.replace("'W=1','-j4'","'W=1','KCFLAGS=-Werror','-j4'")
source=source.replace("'phy-window.patch'","'withdrawal.patch'")
source=source.replace("r=dict(passed=", "obj=build/'drivers/phy/qualcomm/phy-qcom-snps-femto-v2.o'\nr=dict(object_sha256=sha(obj) if obj.exists() else None,object_bytes=obj.stat().st_size if obj.exists() else None,original_builder_sha256='"+hashlib.sha256(original.encode()).hexdigest()+"',Werror=True,passed=")
assert "'/home/cy122/charging-management-20261023/apsd-phy-withdrawal-candidate'" in source
ast.parse(source)
exec(compile(source,'<existing-private-phy-object-builder>','exec'),dict(__file__=str(HERE/'build-private.py'),__name__='__main__'))
