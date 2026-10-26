"""r2 changes private staging headers and adds an explicit install permission contract."""
from pathlib import Path
import copy
import hashlib
import io
import json
import tarfile

HERE = Path(__file__).resolve().parent
PRIVATE = Path('/mnt/e/edk2-samurai-out/kernel475')
source = PRIVATE / 'cohort-r1-private.tar.gz'
target = PRIVATE / 'cohort-r2-private.tar.gz'
assert not target.exists() and not (HERE / 'private-archive-r2-validation.json').exists()
manifest_name = 'cohort475/manifest-private.json'
old_manifest_raw = (PRIVATE / 'cohort-r1/manifest-private.json').read_bytes()
manifest = json.loads(old_manifest_raw)
manifest.update(archive_revision=2, archive_extraction_is_private_staging_not_target_installation=True,
                archive_attributes=dict(uid=0, gid=0, directories_octal='0700', files_octal='0600'),
                target_install_attributes=dict(uid=0, gid=0, directories_octal='0755',
                    module_profile_and_repository_files_octal='0644',
                    apk_owned_file_attributes='use each signed APK ACL; do not inherit transport-tar attributes'),
                drvfs_owner_and_mode_must_not_be_preserved_on_target=True)
new_manifest_raw = (json.dumps(manifest, indent=2) + '\n').encode()
(PRIVATE / 'cohort-r2-manifest-private.json').write_bytes(new_manifest_raw)
before = {}
with tarfile.open(source) as incoming, tarfile.open(target, 'w:gz', format=tarfile.PAX_FORMAT) as outgoing:
    for member in incoming.getmembers():
        assert member.isdir() or member.isfile()
        rel = member.name.rstrip('/')
        assert rel.startswith('cohort475') and '..' not in Path(rel).parts
        item = copy.copy(member)
        item.uid = item.gid = 0
        item.uname = item.gname = 'root'
        item.mode = 0o700 if member.isdir() else 0o600
        item.pax_headers = {key: value for key, value in member.pax_headers.items()
                            if key not in {'uid', 'gid', 'uname', 'gname', 'mode'} and not key.startswith('SCHILY.acl.')}
        if member.isdir():
            outgoing.addfile(item)
        else:
            raw = incoming.extractfile(member).read()
            before[rel] = hashlib.sha256(raw).hexdigest()
            if rel == manifest_name:
                assert raw == old_manifest_raw
                raw = new_manifest_raw
            item.size = len(raw)
            outgoing.addfile(item, io.BytesIO(raw))
count = 0
with tarfile.open(target) as archive:
    for member in archive.getmembers():
        assert member.uid == member.gid == 0 and member.mode == (0o700 if member.isdir() else 0o600)
        if member.isfile():
            raw = archive.extractfile(member).read()
            if member.name == manifest_name:
                assert raw == new_manifest_raw
            else:
                assert hashlib.sha256(raw).hexdigest() == before[member.name]
                relative = member.name.removeprefix('cohort475/')
                assert hashlib.sha256(raw).hexdigest() == manifest['files_sha256'][relative]
                count += 1
report = dict(stage=475, archive_revision=2, passed=True, original_r1_retained=True,
              source_archive_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
              private_archive_sha256=hashlib.sha256(target.read_bytes()).hexdigest(), private_archive_bytes=target.stat().st_size,
              source_manifest_sha256=hashlib.sha256(old_manifest_raw).hexdigest(),
              revised_manifest_sha256=hashlib.sha256(new_manifest_raw).hexdigest(),
              unchanged_apk_index_module_profile_files=count, all_nonmanifest_payload_bytes_preserved=True,
              only_manifest_added_explicit_staging_and_target_permission_contract=True,
              archive_uid=0, archive_gid=0, staging_directories_octal='0700', staging_files_octal='0600',
              target_directories_octal='0755', target_module_profile_files_octal='0644',
              target_owner_uid=0, target_owner_gid=0, tar_extraction_is_not_installation=True,
              phone_accessed=False, installed=False)
(HERE / 'private-archive-r2-validation.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2), flush=True)
