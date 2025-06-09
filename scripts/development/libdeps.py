try:
    from importlib.metadata import distribution
except ImportError:
    from importlib_metadata import distribution  # For Python < 3.8

import re

print(f"{'Package':<30} {'Installed Version':<20} {'Requires-Python'}")
print('-' * 80)

try:
    dist = distribution('esgvoc')
except Exception as e:
    print(f"esgvoc{'':<26} <not installed>{'':<12} <error>")
    raise SystemExit(1)

# Show esgvoc itself
requires_python = dist.metadata.get('Requires-Python', 'Not specified')
version = dist.version
print(f"{'esgvoc':<30} {version:<20} {requires_python}")

# Show direct dependencies only
requires = dist.requires or []
printed = set()

for req in requires:
    pkg = re.split(r'[\[><=;\s]', req)[0]
    if pkg.lower() in printed:
        continue
    printed.add(pkg.lower())

    try:
        dep_dist = distribution(pkg)
        py_req = dep_dist.metadata.get('Requires-Python', 'Not specified')
        ver = dep_dist.version
    except Exception:
        py_req = '<error>'
        ver = '<not installed>'

    print(f"{pkg:<30} {ver:<20} {py_req}")

