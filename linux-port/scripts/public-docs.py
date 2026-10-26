#!/usr/bin/env python3
"""Prepare public copies while retaining private originals in the editing workspace."""
from pathlib import Path
import hashlib
import json
import re
from functools import lru_cache
from fnmatch import fnmatch
from urllib.parse import unquote, urlsplit

CREDENTIAL = re.compile(r'(?:github_pat_[A-Za-z0-9_]{20,}|gh[pousr]_[A-Za-z0-9_]{20,}|-----BEGIN (?:OPENSSH |RSA |EC )?PRIVATE KEY-----)', re.I)
DEVICE = re.compile(r'(?<![0-9a-f])(?:0x)?[0-9a-f]{8}(?![0-9a-f])', re.I)
DEVICE_BYTES = re.compile(r'(?<![0-9a-f])[0-9a-f]{2}(?:[ :,-]+[0-9a-f]{2}){3}(?![0-9a-f])', re.I)
DECIMAL = re.compile(r'(?<!\d)\d{9,10}(?!\d)')
UUID = re.compile(r'\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b', re.I)
BOOT = re.compile(r'(?:boot.?id|boot.?identity|expected.?boot|source.?boot|current.?boot)[^\r\n]{0,150}', re.I)
MAC = re.compile(r'\b(?:[0-9a-f]{2}:){5}[0-9a-f]{2}\b', re.I)
PUBLIC_MAC = {'00:00:00:00:00:00', 'ff:ff:ff:ff:ff:ff', '02:00:00:00:00:00', '02:11:22:33:44:55', '11:22:33:44:55:66'}


@lru_cache(maxsize=None)
def private_identifiers(root):
    path = root/'out/publish-2026-10-14/private-export-identifiers.json'
    return set(json.loads(path.read_text())) if path.is_file() else set()


@lru_cache(maxsize=None)
def public_uuids(root):
    path=root/'linux-port/scripts/public-uuid-allowlist.json'
    return set(json.loads(path.read_text())['values']) if path.is_file() else set()


def sanitize_text(text, identifiers=frozenset()):
    if CREDENTIAL.search(text):
        raise ValueError('Credential material must remain private; public export refused.')
    def device(match):
        value = match[0].lower().removeprefix('0x')
        if value not in identifiers:
            return match[0]
        return '0x00000000' if match[0].lower().startswith('0x') else 'PRIVATE_DEVICE_ID'
    text = DEVICE.sub(device, text)
    text = DEVICE_BYTES.sub(lambda m: 'XX XX XX XX' if re.sub(r'[^0-9a-f]', '', m[0].lower()) in identifiers else m[0], text)
    numeric_ids = {int(value,16) for value in identifiers}
    text = DECIMAL.sub(lambda m: 'PRIVATE_DEVICE_ID' if int(m[0]) in numeric_ids else m[0], text)
    text = re.sub(r'(<meta\b[^>]*\bname=["\'](?:csrf-token|fetch-nonce|request-id)["\'][^>]*\bcontent=["\'])[^"\']+',r'\1PRIVATE_TOKEN',text,flags=re.I)
    lines = []
    for line in text.splitlines(keepends=True):
        if BOOT.search(line):
            line = UUID.sub('PRIVATE_BOOT_ID', line)
        line = MAC.sub(lambda m: m[0] if m[0].lower() in PUBLIC_MAC else 'PRIVATE_MAC', line)
        lines.append(line)
    return ''.join(lines)


def sanitize_json(value, context='', identifiers=frozenset()):
    if isinstance(value, dict):
        return {key: sanitize_json(item, context+'.'+key, identifiers) for key,item in value.items()}
    if isinstance(value, list):
        return [sanitize_json(item, context, identifiers) for item in value]
    if isinstance(value, str):
        key = context.rsplit('.',1)[-1].lower()
        if key in {'password','psk','passphrase','private_key','ssh_private_key'}:
            return 'PRIVATE_VALUE'
        if key == 'ssid' and value:
            return 'PRIVATE_SSID'
        if key in {'imei','meid','imsi','iccid','subscriber_id','phone_number','line_number','serial','serialno','android_serial'} and value:
            return 'PRIVATE_IDENTIFIER'
        if 'boot' in context.lower() and 'guid' not in key:
            value = UUID.sub('PRIVATE_BOOT_ID', value)
        return sanitize_text(value, identifiers)
    if isinstance(value, int) and value in {int(item,16) for item in identifiers}:
        return None
    return value


def private_evidence_links(root, relative, text):
    if relative.suffix != '.md':
        return text
    manifest_path = root/'linux-port/scripts/docs-sync-manifest.json'
    if not manifest_path.is_file():
        return text
    manifest = json.loads(manifest_path.read_text())
    def replace(match):
        url = match[2] or match[3]
        parts = urlsplit(url)
        if parts.scheme or parts.netloc or not parts.path:
            return match[0]
        target = (root/relative.parent/unquote(parts.path)).resolve()
        if not target.is_relative_to(root.resolve()):
            return match[0]
        name = target.relative_to(root.resolve()).as_posix()
        excluded = any(fnmatch(name,pattern) for pattern in manifest.get('exclude',[]))
        retained = any(fnmatch(name,pattern) for pattern in manifest.get('include_overrides',[]))
        return match[1]+'（本地私人证据）' if excluded and not retained else match[0]
    return re.sub(r'\[([^\]\n]+)\]\((?:<([^>\n]+)>|([^\s)\n]+))\)',replace,text)


def public_bytes(root, relative, raw=None):
    relative = Path(relative)
    identifiers = private_identifiers(root)
    allowed_uuids = public_uuids(root)
    raw = (root/relative).read_bytes() if raw is None else raw
    try:
        text = raw.decode('utf-16') if raw.startswith((b'\xff\xfe', b'\xfe\xff')) else raw.decode('utf-8-sig')
    except UnicodeDecodeError:
        raise ValueError('Unreviewed binary in documentation export: '+str(relative))
    # Preserve the source digest, and verify the redacted snapshot with its own digest.
    if relative.name == 'manifest.json' and 'docs-before-maintenance-' in str(relative.parent):
        entries = json.loads(text)
        for entry in entries:
            snapshot = relative.parent / entry.get('snapshot_path', entry['path'])
            exported = public_bytes(root, snapshot)
            entry['private_original_sha256'] = entry.get('private_original_sha256', entry['sha256'])
            entry['sha256'] = hashlib.sha256(exported).hexdigest()
            entry['bytes'] = len(exported)
            entry['public_redacted_copy'] = True
        return (json.dumps(entries,ensure_ascii=False,indent=2)+'\n').encode()
    if relative.suffix == '.json':
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            return sanitize_text(text, identifiers).encode()
        result = sanitize_json(data, identifiers=identifiers)
        if result != data:
            text=json.dumps(result,ensure_ascii=False,indent=2)+'\n'
    text=sanitize_text(text, identifiers)
    text=UUID.sub(lambda m:m[0] if m[0].lower() in allowed_uuids else 'PRIVATE_UUID',text)
    return private_evidence_links(root,relative,text).encode()
