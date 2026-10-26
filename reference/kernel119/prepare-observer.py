from pathlib import Path
root=Path('/mnt/e/RealmeX2Pro edk2/reference')
t=(root/'kernel115/read-early-eud.ps1').read_text().replace('kernel115','kernel119')
(root/'kernel119/read-early-eud.ps1').write_text(t)
print('K119_BOUNDED_EUD_OBSERVER_PREPARED')
