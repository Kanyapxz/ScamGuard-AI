from __future__ import annotations

import time
import base64
import requests
from typing import Any, Dict, List

from config import SAFE_BROWSING_API_KEY, LINK_CHECK_TIMEOUT, VIRUSTOTAL_API_KEY
from nlp.preprocess import extract_urls


class LinkChecker:
    SAFE_BROWSING_URL = "https://safebrowsing.googleapis.com/v4/threatMatches:find"
    URLHAUS_URL       = "https://urlhaus-api.abuse.ch/v1/url/"
    VT_SCAN_URL       = "https://www.virustotal.com/api/v3/urls"
    VT_REPORT_URL     = "https://www.virustotal.com/api/v3/urls/{id}"

    def __init__(
        self,
        api_key: str = SAFE_BROWSING_API_KEY,
        vt_key: str = VIRUSTOTAL_API_KEY,
        timeout: int = LINK_CHECK_TIMEOUT
    ):
        self.api_key = api_key
        self.vt_key  = vt_key
        self.timeout = timeout

    def is_available(self) -> bool:
        return True

    # ── Google Safe Browsing ──────────────────────
    def _check_google(self, urls: List[str]) -> Dict[str, List[str]]:
        if not self.api_key:
            return {}
        try:
            payload = {
                "client": {"clientId": "scamguard-ai", "clientVersion": "1.0.0"},
                "threatInfo": {
                    "threatTypes": ["MALWARE","SOCIAL_ENGINEERING","UNWANTED_SOFTWARE","POTENTIALLY_HARMFUL_APPLICATION"],
                    "platformTypes": ["ANY_PLATFORM"],
                    "threatEntryTypes": ["URL"],
                    "threatEntries": [{"url": u} for u in urls],
                },
            }
            res = requests.post(
                f"{self.SAFE_BROWSING_URL}?key={self.api_key}",
                json=payload, timeout=self.timeout
            )
            res.raise_for_status()
            matched: Dict[str, List[str]] = {}
            for item in res.json().get("matches", []):
                u = item.get("threat", {}).get("url", "")
                t = item.get("threatType", "UNKNOWN")
                if u:
                    matched.setdefault(u, []).append(t)
            return matched
        except Exception:
            return {}

    # ── URLhaus ───────────────────────────────────
    def _check_urlhaus(self, url: str) -> str | None:
        try:
            res = requests.post(
                self.URLHAUS_URL,
                data={"url": url},
                timeout=self.timeout
            )
            res.raise_for_status()
            data = res.json()
            if data.get("query_status") == "is_page" and data.get("url_status") == "online":
                tags = data.get("tags") or []
                return tags[0] if tags else "MALWARE"
            return None
        except Exception:
            return None

    # ── VirusTotal ────────────────────────────────
    def _check_virustotal(self, url: str) -> Dict[str, Any] | None:
        if not self.vt_key:
            return None
        try:
            headers = {"x-apikey": self.vt_key}

            # Step 1 — submit URL
            res = requests.post(
                self.VT_SCAN_URL,
                headers=headers,
                data={"url": url},
                timeout=self.timeout
            )
            res.raise_for_status()
            analysis_id = res.json().get("data", {}).get("id", "")
            if not analysis_id:
                return None

            # URL id = base64(url) แบบ url-safe ไม่มี padding
            url_id = base64.urlsafe_b64encode(url.encode()).decode().rstrip("=")

            # Step 2 — รอสักครู่แล้วดึงผล
            time.sleep(2)
            report = requests.get(
                self.VT_REPORT_URL.format(id=url_id),
                headers=headers,
                timeout=self.timeout
            )
            report.raise_for_status()
            stats = report.json().get("data", {}).get("attributes", {}).get("last_analysis_stats", {})

            malicious  = stats.get("malicious", 0)
            suspicious = stats.get("suspicious", 0)
            total      = sum(stats.values()) or 1

            return {
                "malicious":  malicious,
                "suspicious": suspicious,
                "total":      total,
                "ratio":      f"{malicious}/{total}",
            }
        except Exception:
            return None

    # ── Main ──────────────────────────────────────
    def check_urls(self, urls: List[str]) -> Dict[str, Any]:
        seen, clean_urls = set(), []
        for u in urls:
            u = (u or "").strip()
            if u and u not in seen:
                seen.add(u); clean_urls.append(u)

        if not clean_urls:
            return {
                "available": True, "checked_urls": [],
                "results": [],
                "summary": {"checked_count": 0, "unsafe_count": 0, "clean_count": 0}
            }

        google_hits = self._check_google(clean_urls)
        results = []
        unsafe_count = clean_count = 0

        for url in clean_urls:
            threats: List[str] = list(google_hits.get(url, []))
            vt_result = None

            # URLhaus
            if not threats:
                uh = self._check_urlhaus(url)
                if uh:
                    threats.append(f"URLHAUS:{uh}")

            # VirusTotal
            vt_result = self._check_virustotal(url)
            if vt_result and vt_result["malicious"] > 0:
                threats.append(f"VIRUSTOTAL:{vt_result['ratio']} engines")

            if threats:
                results.append({
                    "url": url,
                    "status": "unsafe",
                    "threat_types": threats,
                    "virustotal": vt_result,
                })
                unsafe_count += 1
            else:
                results.append({
                    "url": url,
                    "status": "clean",
                    "threat_types": [],
                    "virustotal": vt_result,
                })
                clean_count += 1

        return {
            "available": True,
            "checked_urls": clean_urls,
            "results": results,
            "summary": {
                "checked_count": len(clean_urls),
                "unsafe_count": unsafe_count,
                "clean_count": clean_count,
            },
        }

    def check_text(self, text: str) -> Dict[str, Any]:
        return self.check_urls(extract_urls(text))