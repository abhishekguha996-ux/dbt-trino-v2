"""Extract locked tar inputs into new guest directories with bounded paths and sizes."""

from pathlib import Path, PurePosixPath
import posixpath
import shutil
import tarfile


def safe_extract(archive, destination, max_bytes=512 * 1024 * 1024):
    destination = Path(destination)
    if destination.exists() or destination.is_symlink():
        raise ValueError("Extraction destination must be new")
    with tarfile.open(archive, "r:gz") as tar:
        members = tar.getmembers()
        if len(members) > 100000 or sum(m.size for m in members) > max_bytes:
            raise ValueError("Archive exceeds extraction budget")
        names = {}
        links = set()
        for member in members:
            path = PurePosixPath(member.name)
            if path.is_absolute() or ".." in path.parts or not path.parts:
                raise ValueError("Unsafe archive path")
            name = str(path)
            if name in names or not (member.isdir() or member.isfile() or member.issym()):
                raise ValueError("Duplicate path or unsupported archive member")
            names[name] = member
            if member.issym():
                links.add(name)
        for name, member in names.items():
            if any(str(parent) in links for parent in PurePosixPath(name).parents):
                raise ValueError("Archive member descends through a symlink")
            if member.issym():
                if posixpath.isabs(member.linkname):
                    raise ValueError("Absolute symlink")
                target = posixpath.normpath(posixpath.join(posixpath.dirname(name), member.linkname))
                if target == ".." or target.startswith("../"):
                    raise ValueError("Symlink escapes archive")
                if target in links or any(str(p) in links for p in PurePosixPath(target).parents):
                    raise ValueError("Symlink chains are not accepted")
        destination.mkdir(parents=False)
        # Write links last so file writes cannot follow archive-controlled links.
        for name, member in names.items():
            target = destination / name
            target.parent.mkdir(parents=True, exist_ok=True)
            if member.isdir():
                target.mkdir(exist_ok=True)
            elif member.isfile():
                with tar.extractfile(member) as source, target.open("xb") as output:
                    shutil.copyfileobj(source, output)
                target.chmod(0o755 if member.mode & 0o111 else 0o644)
        for name in links:
            (destination / name).symlink_to(names[name].linkname)
