from urllib.parse import urljoin
import httpx


class AppFolioReportClient:
    def __init__(self, base_url: str, client_id: str, client_secret: str, timeout: float = 30):
        self.base_url = base_url.rstrip("/") + "/"
        self.auth = (client_id, client_secret)
        self.timeout = timeout

    async def iter_standard_report(self, report_name: str, limit: int = 10):
        if not report_name.replace("_", "").replace("-", "").isalnum():
            raise ValueError("Invalid standard report name")
        url = urljoin(self.base_url, f"api/v2/reports/{report_name}.json")
        async for page in self._iter_url(url, limit, method="POST"):
            yield page

    async def iter_saved_report(self, saved_report_id: str, limit: int = 10):
        if not saved_report_id.replace("-", "").isalnum():
            raise ValueError("Invalid saved report ID")
        url = urljoin(self.base_url, f"api/v2/reports/saved/{saved_report_id}.json")
        async for page in self._iter_url(url, limit):
            yield page

    async def _iter_url(self, url: str, limit: int, method: str = "GET"):
        payload = {"limit": min(limit, 5000), "paginate_results": True}
        seen_urls: set[str] = set()
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        async with httpx.AsyncClient(
            auth=self.auth,
            headers=headers,
            timeout=self.timeout,
        ) as client:
            while url:
                if url in seen_urls:
                    raise RuntimeError(f"AppFolio pagination loop detected at {url}")
                seen_urls.add(url)
                if method == "POST":
                    response = await client.post(url, json=payload)
                else:
                    response = await client.get(url)
                try:
                    response.raise_for_status()
                except httpx.HTTPStatusError as exc:
                    request_id = response.headers.get("x-request-id")
                    suffix = f" (request ID: {request_id})" if request_id else ""
                    raise RuntimeError(
                        f"AppFolio returned HTTP {response.status_code} for "
                        f"{response.request.url}{suffix}"
                    ) from exc
                payload = response.json()
                results = payload.get("results")
                if not isinstance(results, list):
                    raise ValueError("AppFolio response is missing a results array")
                yield results
                next_page = payload.get("next_page_url")
                url = urljoin(self.base_url, next_page.lstrip("/")) if next_page else ""
                method = "GET"

    # Backward-compatible alias used by earlier callers.
    async def iter_report(self, saved_report_id: str, limit: int = 10):
        async for page in self.iter_saved_report(saved_report_id, limit):
            yield page
