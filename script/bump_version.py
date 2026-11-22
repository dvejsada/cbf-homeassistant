"""Set the integration version in manifest.json.

Usage: python script/bump_version.py 0.2.0
"""

from __future__ import annotations

import json
from pathlib import Path
import re
import sys

MANIFEST = Path(__file__).parent.parent / "custom_components" / "cbf" / "manifest.json"
# MAJOR.MINOR.PATCH with an optional pre-release like -beta.1 (dot-separated,
# non-empty identifiers), so Home Assistant accepts it as a valid SemVer version.
VERSION_RE = re.compile(r"\d+\.\d+\.\d+(-[0-9A-Za-z]+(\.[0-9A-Za-z]+)*)?")


def main() -> int:
    if len(sys.argv) != 2 or not VERSION_RE.fullmatch(sys.argv[1].removeprefix("v")):
        print(__doc__.strip())
        return 1
    version = sys.argv[1].removeprefix("v")
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    old = manifest["version"]
    manifest["version"] = version
    MANIFEST.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Version {old} -> {version}\n")
    print("Next steps:")
    print(f'  git commit -am "Release v{version}"')
    print("  git push")
    print(f"  git tag v{version}")
    print(f"  git push origin v{version}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
