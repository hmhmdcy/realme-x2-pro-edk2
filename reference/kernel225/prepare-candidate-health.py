from pathlib import Path

here=Path(__file__).resolve().parent
text=(here.parent/'kernel224/final-health.py').read_text()
text=text.replace('k224-final-health','k225-candidate-health').replace('k224-baseline','k225-baseline').replace('stage=224','stage=225')
text=text.replace("here/'final-health-validation.json'","here/'candidate-health-validation.json'").replace("host.PRIVATE/'final-health-host-private.log'","host.PRIVATE/'candidate-health-host-private.log'")
# Actual installed framework and transaction/full-mode history remain stage224.
assert "k224-r11-package-candidates" in text and "k224-r11-package-transaction" in text and "k224-full-mode-experiment" in text
compile(text,'candidate-final-health.py','exec');(here/'candidate-final-health.py').write_text(text)
print('Read-only final candidate health prepared against actual installed r11 payloads.')
