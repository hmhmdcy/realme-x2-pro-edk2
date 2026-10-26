"""Refresh service caches after creating a previously absent per-user directory."""
from pathlib import Path
import ast
R=Path(__file__).resolve().parent
s=(R/'verify-snapshot-dbus.py').read_text()
s=s.replace('k240-snapshot-dbus-activation-r2','k240-snapshot-dbus-activation-r3')
s=s.replace("existing=bool(d.NameHasOwner('org.gnome.Snapshot'))", "d.ReloadConfig()\nexisting=bool(d.NameHasOwner('org.gnome.Snapshot'))")
s=s.replace('preexisting_snapshot_preserved=data', 'session_service_cache_reloaded=True,preexisting_snapshot_preserved=data')
ast.parse(s);(R/'verify-snapshot-dbus-r3.py').write_text(s)
print('Native D-Bus service cache refresh prepared; existing services are retained')
