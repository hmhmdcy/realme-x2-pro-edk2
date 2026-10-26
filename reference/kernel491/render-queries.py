"""Reuse the tested transport renderer with491 plan/gates; no old transaction."""
from pathlib import Path
import hashlib
import importlib.util


def render(work, plan, mapping, modes, directories, bundle_hash, gate, charging):
    path = Path(__file__).resolve().parent.parent / 'kernel481/render-queries.py'
    assert hashlib.sha256(path.read_bytes()).hexdigest() == '2e3fa0b2f590e730b5b8e282cba163c6883adc3cebff11ab28ca9274519b01e5'
    assert plan['stage'] == 491 and plan['window_id'].startswith('k491-package-only-')
    assert not plan['modules_or_private_profiles_replaced'] and not plan['persistent_repository_created']
    spec = importlib.util.spec_from_file_location('query_renderer481_for491', path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    # The parent renderer contains no transport or target execution. Its queries
    # take every path, byte hash, version, read-only module/profile and gate from
    # this new plan. No former WINDOW, owner, launch or state is copied.
    module.render(work, plan, mapping, modes, directories, bundle_hash, gate, charging)
