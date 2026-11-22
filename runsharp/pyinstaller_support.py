"""Resource and version helpers for the Windows executable build."""

from pathlib import Path


def collect_windows_ssl_binaries(prefixes):
    """Find OpenSSL DLLs beside the build interpreter, preferring its environment."""
    found = {}
    for prefix in prefixes:
        for relative_dir in (Path('Library') / 'bin', Path('DLLs'), Path()):
            directory = Path(prefix) / relative_dir
            for pattern in ('libcrypto-*.dll', 'libssl-*.dll'):
                for dll in sorted(directory.glob(pattern)):
                    found.setdefault(dll.name.lower(), dll.resolve())

    for family in ('libcrypto-', 'libssl-'):
        if not any(name.startswith(family) for name in found):
            raise RuntimeError('Unable to find the %s runtime DLL' % family.rstrip('-'))
    return [(str(found[name]), '.') for name in sorted(found)]


def collect_windows_resources(project_root):
    """Return PyInstaller data pairs independently of the working directory."""
    root = Path(project_root).resolve()
    databases = root / 'sharppy' / 'databases'
    resources = []

    for name in ('PW-mean-inches.txt', 'PW-stdev-inches.txt',
                 'sars_hail.txt', 'sars_supercell.txt'):
        source = databases / name
        if not source.is_file():
            raise FileNotFoundError('Missing SHARPpy resource: %s' % source)
        resources.append((str(source), 'sharppy/databases'))

    groups = (
        (databases / 'sars' / 'hail', '*', 'sharppy/databases/sars/hail'),
        (databases / 'sars' / 'supercell', '*', 'sharppy/databases/sars/supercell'),
        (databases / 'shapefiles', '*', 'sharppy/databases/shapefiles'),
        (root / 'datasources', '*.xml', 'sharppy/datasources'),
        (root / 'datasources', '*.csv', 'sharppy/datasources'),
        (root / 'rc', '*.png', 'rc'),
    )
    for directory, pattern, destination in groups:
        files = [path for path in sorted(directory.glob(pattern)) if path.is_file()]
        if not files:
            raise FileNotFoundError('Missing SHARPpy resources: %s' % (directory / pattern))
        resources.extend((str(path), destination) for path in files)
    return resources


def write_version_runtime_hook(workpath, version_info):
    """Freeze Versioneer metadata in build output without modifying source files."""
    hook = Path(workpath) / 'sharppy_version_runtime.py'
    hook.parent.mkdir(parents=True, exist_ok=True)
    source = (
        'import sys\n'
        'from types import ModuleType\n'
        '\n'
        '_sharppy_version = ModuleType("sharppy._version")\n'
        'def _sharppy_get_versions():\n'
        '    return %r\n'
        '_sharppy_version.get_versions = _sharppy_get_versions\n'
        'sys.modules["sharppy._version"] = _sharppy_version\n'
    ) % dict(version_info)
    hook.write_text(source, encoding='utf-8')
    return hook
