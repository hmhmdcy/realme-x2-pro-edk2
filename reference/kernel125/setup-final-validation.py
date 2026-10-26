from pathlib import Path
r=Path('/mnt/e/RealmeX2Pro edk2');ref=r/'reference/kernel125'
code=(r/'reference/kernel124/record-build-and-package.py').read_text().replace('124','125')
code=code.replace('sm8150-cphy-power-7.3.patch','sm8150-cpas-iova-7.3.patch').replace("cwd=v/'camera123/kernel'","cwd=v/'camera124/kernel'").replace('patch_applies_cleanly_to_123','patch_applies_cleanly_to_124')
# Generate the final checkers from their direct preceding version.
start=code.index("code=(r/'reference/kernel123/verify-package.py')")
code=code[:start]+"exec(compile((ref/'verify-package.py').read_text(),'verify-package125','exec'),{})\nexec(compile((ref/'compare-modules-and-health.py').read_text(),'compare-modules-health125','exec'),{})\nprint('K125_BUILD_PACKAGE_SOURCE_AND_PHONE_HEALTH_VALIDATED')\n"
(ref/'record-build-and-package.py').write_text(code)
(ref/'verify-package.py').write_text((r/'reference/kernel124/verify-package.py').read_text().replace('124','125'))
code=(r/'reference/kernel124/compare-modules-and-health.py').read_text().replace('124','125').replace('a=modules(123);b=modules(125)','a=modules(124);b=modules(125)').replace('changed_vs123','changed_vs124')
code=code.replace("assert 'drivers/media/platform/qcom/camss/qcom-camss.ko' in changes","assert changes==['drivers/media/platform/qcom/camss/qcom-camss.ko']")
(ref/'compare-modules-and-health.py').write_text(code)
(ref/'verify-syntax.py').write_text((r/'reference/kernel124/verify-syntax.py').read_text().replace('124','125'))
code=(r/'reference/kernel124/close-host-volumes.py').read_text().replace('124','125')
(ref/'close-host-volumes.py').write_text(code)
print('K125_FINAL_VALIDATION_SCRIPTS_READY')
