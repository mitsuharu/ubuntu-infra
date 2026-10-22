#!/usr/bin/env python3
"""公式READMEの検証付き手順から更新候補を作る。取得したコードは実行しない。"""

import hashlib
import json
import re
import urllib.request
from pathlib import Path

README_URL = "https://raw.githubusercontent.com/AikidoSec/safe-chain/main/README.md"
LATEST_URL = "https://api.github.com/repos/AikidoSec/safe-chain/releases/latest"
RELEASE_FILE = Path(__file__).resolve().parents[1] / "shells/safe-chain-release.sh"


def parse_installation(readme):
    section = re.search(
        r"^### Unix/Linux/macOS\s*\n```shell\n(.*?)\n```", readme, re.M | re.S
    )
    if section is None:
        raise ValueError("公式READMEのUnix/Linux/macOS手順が見つかりません")
    command = " ".join(section.group(1).replace("\\\n", " ").split())
    match = re.fullmatch(
        r"curl -fsSL https://github\.com/AikidoSec/safe-chain/releases/download/"
        r"(?P<version>[0-9]+\.[0-9]+\.[0-9]+)/install-safe-chain\.sh "
        r'-o /tmp/install-safe-chain\.sh && echo "(?P<sha256>[a-f0-9]{64}) '
        r'/tmp/install-safe-chain\.sh" \| sha256sum -c - '
        r"&& sh /tmp/install-safe-chain\.sh && rm /tmp/install-safe-chain\.sh",
        command,
    )
    if match is None:
        raise ValueError("公式インストール手順が変更されています。手動で確認してください")
    return match.group("version"), match.group("sha256")


def fetch(url):
    request = urllib.request.Request(url, headers={"User-Agent": "ubuntu-infra-safe-chain-update"})
    with urllib.request.urlopen(request, timeout=60) as response:
        return response.read()


def update(readme, release, download, destination):
    version, digest = parse_installation(readme)
    if release.get("tag_name") != version or release.get("draft") or release.get("prerelease"):
        raise ValueError("最新の正式リリースとREADMEのバージョンが一致しません")
    url = f"https://github.com/AikidoSec/safe-chain/releases/download/{version}/install-safe-chain.sh"
    if hashlib.sha256(download(url)).hexdigest() != digest:
        raise ValueError("インストーラーのSHA-256が公式READMEと一致しません")
    content = (
        '#!/usr/bin/env bash\n\n'
        f'SAFE_CHAIN_RELEASE="{version}"\n'
        f'SAFE_CHAIN_INSTALLER_SHA256="{digest}"\n'
    )
    if destination.read_text() == content:
        print(f"Safe Chain {version}: 更新なし")
        return False
    destination.write_text(content)
    print(f"Safe Chain {version}: バージョンとSHA-256を更新しました")
    return True


def main():
    update(
        fetch(README_URL).decode("utf-8"),
        json.loads(fetch(LATEST_URL)),
        fetch,
        RELEASE_FILE,
    )


if __name__ == "__main__":
    main()
