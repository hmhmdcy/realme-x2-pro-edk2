"""Correct the schema assertion: resolutionInfo is a repeated reference list."""
from pathlib import Path
here=Path(__file__).resolve().parent
source=(here/'crosscheck-modes-r3.py').read_text().replace('modes-r3','modes-r4').replace('vendor-mode-r3','vendor-mode-r4').replace('vendor-r3-xml','vendor-r4-xml')
source=source.replace("resolution_node.attrib.get('minOccurs')=='0'","resolution_node.attrib.get('maxOccurs')=='unbounded'")
exec(compile(source,'mode-r4-analysis-projection','exec'))
