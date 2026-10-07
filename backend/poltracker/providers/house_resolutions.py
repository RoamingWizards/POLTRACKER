"""House resolutions as published by GPO on govinfo: the official record of who the House elected to, or removed from, standing committees.

Bulk text per session: https://www.govinfo.gov/bulkdata/BILLS/{congress}/{session}/hres/BILLS-{congress}-{session}-hres.zip (public, no key). Only the ENGROSSED
version (suffix `eh`, the text the House agreed to) is returned: an introduced resolution the House never adopted establishes nothing. This module only
fetches and unpacks; reading the resolutions is committee_history.py. Retries are handled here, at the provider boundary.
"""

import io
import logging
import re
import time
import zipfile
from pathlib import Path

import httpx

from .base import ProviderError

log = logging.getLogger(__name__)

BULK = "https://www.govinfo.gov/bulkdata/BILLS/{congress}/{session}/hres/BILLS-{congress}-{session}-hres.zip"
DOC = "https://www.govinfo.gov/content/pkg/BILLS-{congress}hres{number}eh/xml/BILLS-{congress}hres{number}eh.xml"
ENGROSSED = re.compile(r"BILLS-(\d+)hres(\d+)eh\.xml$")


class HouseResolutionsProvider:
    name = "house.resolutions"

    def __init__(self, client: httpx.Client | None = None, cache_dir: Path | None = None, attempts: int = 3, pause: float = 2.0):
        self._client = client or httpx.Client(timeout=120, follow_redirects=True, headers={"User-Agent": "POLTRACKER/0.1"})
        self._cache = Path(cache_dir) if cache_dir else None
        self._attempts = attempts
        self._pause = pause
        self.requests_made = 0

    def _download(self, url: str) -> bytes:
        last: Exception | None = None
        for attempt in range(self._attempts):
            self.requests_made += 1
            try:
                resp = self._client.get(url)
                if resp.status_code == 200:
                    return resp.content
                if resp.status_code == 404:
                    raise ProviderError(f"govinfo: not found: {url}")
                last = ProviderError(f"govinfo: HTTP {resp.status_code}")
            except httpx.HTTPError as exc:
                last = ProviderError(f"govinfo: network error ({type(exc).__name__})")
            time.sleep(self._pause * (attempt + 1))
        raise last or ProviderError("govinfo: download failed")

    def _zip(self, congress: int, session: int) -> bytes | None:
        path = self._cache / f"BILLS-{congress}-{session}-hres.zip" if self._cache else None
        if path is not None and path.exists():
            return path.read_bytes()
        try:
            data = self._download(BULK.format(congress=congress, session=session))
        except ProviderError as exc:
            if "not found" in str(exc):
                return None  # a session that has not happened yet
            raise
        if path is not None:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        return data

    def engrossed_documents(self, congress: int) -> list[tuple[str, str, bytes]]:
        """(label, url, xml) for every engrossed House resolution of a Congress."""
        out: list[tuple[str, str, bytes]] = []
        for session in (1, 2):
            data = self._zip(congress, session)
            if data is None:
                continue
            try:
                with zipfile.ZipFile(io.BytesIO(data)) as zf:
                    for name in zf.namelist():
                        m = ENGROSSED.search(name)
                        if m and int(m.group(1)) == congress:
                            out.append((f"H.Res. {m.group(2)}", DOC.format(congress=congress, number=m.group(2)), zf.read(name)))
            except zipfile.BadZipFile as exc:
                raise ProviderError("govinfo: the bulk file was not a valid zip") from exc
        return sorted(out, key=lambda d: int(d[0].split()[-1]))
