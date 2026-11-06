"""Client of the "Interactive budget" web application (LSFinance by LSoft) at budget.minfin.am:82.

How the site works (see docs/en/sources.md):

* ``GET /`` creates a server-side session: the page contains ``sessid`` (hidden input)
  and sets the cookie ``bcsession``; the left menu lists the three reports with the
  annual plan of the current year.
* ``GET /param.php?sessid=..&page=site_b`` returns the form of a report; the form is
  submitted as ``POST /param.php`` with ``ACTION=VIEW``, the year (``SITE_YEAR``, an index:
  1 = the latest year), filters (checkbox lists ``mid[]``, ``grp[]``, …) and grouping
  (``site_NN1``…``site_NN7``). The server stores the query in the session.
* ``GET /Popup.php?page=SITE_BG&uid=1&data=.&sessid=..`` returns the result of the stored
  query as a w2ui grid (expenditures: SITE_BG, revenues: SITE_DG). The deficit form shows
  its grid directly in the POST response.
* ``GET /xml/xmlopen.php?page=SITE_B_XLS&lang=1`` writes an Excel export of the last
  result to ``xml/temp/<id>.xls`` and returns a link to it.
* ``GET /Popup.php?page=SITE_C&uid=1&data=<PARAM>{line};{year index};</PARAM>`` returns
  the contracts of an expenditure line (the line id is column c20 of a result grouped by
  "contracts").
"""

from __future__ import annotations

import logging
import re
import threading
import time

import requests

from . import config
from .parsers.forms import FormPage, parse_form
from .parsers.grid import Grid, parse_grid

log = logging.getLogger(__name__)


class SiteError(RuntimeError):
    pass


class Site:
    """One server-side session. Not thread safe: the server keeps the last query per session."""

    def __init__(self, delay: float = config.HTTP_DELAY) -> None:
        self.delay = delay
        self._last = 0.0
        self.session: requests.Session | None = None
        self.sessid: str | None = None
        self.start_page: str | None = None
        self._forms_loaded: set[str] = set()

    # -- low level ---------------------------------------------------------
    def _request(self, method: str, path: str, read_timeout: float = config.HTTP_TIMEOUT, retries: int = config.HTTP_RETRIES,
                 **kw) -> requests.Response:
        if self.session is None:
            self.start()
        url = path if path.startswith("http") else f"{config.BASE_URL}/{path.lstrip('/')}"
        last_exc: Exception | None = None
        for attempt in range(1, retries + 1):
            idle = time.monotonic() - self._last
            if self.delay - idle > 0:
                time.sleep(self.delay - idle)
            if idle > config.HTTP_IDLE_RECONNECT:
                # the server drops idle keep-alive connections without closing them, and a request
                # sent on such a connection hangs: reconnect after a pause (a new TLS handshake takes ~3 s)
                self.session.close()
            try:
                t0 = time.monotonic()
                r = self._call(method, url, read_timeout, **kw)
                self._last = time.monotonic()
                log.debug("%s %s -> %s, %d bytes, %.1fs", method, path[:60], r.status_code, len(r.content), self._last - t0)
                if r.status_code >= 500:
                    raise requests.HTTPError(f"HTTP {r.status_code}", response=r)
                r.raise_for_status()
                r.encoding = "utf-8"
                return r
            except requests.RequestException as exc:  # network error, reset by peer, 5xx
                last_exc = exc
                self._last = time.monotonic()
                self.session.close()  # do not reuse a connection that failed
                if attempt < retries:
                    backoff = 10 * attempt
                    log.warning("%s %s failed (%s), retry %d in %ds", method, path[:80], exc, attempt, backoff)
                    time.sleep(backoff)
        raise SiteError(f"{method} {url} failed after {retries} attempts: {last_exc}") from last_exc

    def _call(self, method: str, url: str, read_timeout: float, **kw) -> requests.Response:
        """One HTTP request with a hard wall-clock deadline.

        Some requests hang in the TLS handshake or between packets far beyond the socket
        timeouts of ``requests``; the request runs in a daemon thread and is abandoned
        (and counted as a timeout) when the deadline passes."""
        deadline = config.HTTP_CONNECT_TIMEOUT + read_timeout + 15
        box: dict = {}

        def run() -> None:
            try:
                box["r"] = self.session.request(method, url, timeout=(config.HTTP_CONNECT_TIMEOUT, read_timeout), **kw)
                _ = box["r"].content  # read the body inside the deadline
            except BaseException as exc:  # noqa: BLE001 - re-raised in the caller
                box["e"] = exc

        t = threading.Thread(target=run, daemon=True)
        t.start()
        t.join(deadline)
        if t.is_alive():
            raise requests.Timeout(f"no complete response in {deadline:.0f} s")
        if "e" in box:
            raise box["e"]
        return box["r"]

    def start(self) -> str:
        """Open a new server-side session."""
        self.session = requests.Session()
        self.session.headers["User-Agent"] = config.USER_AGENT
        self._forms_loaded = set()
        r = self._request("GET", "/")
        m = re.search(r'name="sessid" value="([0-9a-f]+)"', r.text)
        if not m:
            raise SiteError("no sessid on the start page")
        self.sessid = m.group(1)
        self.start_page = r.text
        log.debug("new session %s", self.sessid)
        return r.text

    def restart(self) -> None:
        self.session = None
        self.start()

    # -- forms and results --------------------------------------------------
    def form(self, page: str) -> str:
        r = self._request("GET", "/param.php", params={
            "sessid": self.sessid, "lang": 1, "custid": 0, "page": page, "isdoc": 0, "tm": int(time.time() * 1000)})
        self._forms_loaded.add(page)
        return r.text

    def view(self, page: str, fields: list[tuple[str, str]], read_timeout: float = config.HTTP_RESULT_TIMEOUT) -> str:
        """Submit the form of ``page`` (ACTION=VIEW) and return the response page."""
        if page not in self._forms_loaded:
            self.form(page)
        data = [("page", page), ("sessid", self.sessid), ("ACTION", "VIEW")] + [(k, str(v)) for k, v in fields]
        return self._request("POST", "/param.php", read_timeout=read_timeout, data=data).text

    def popup(self, name: str, data: str = ".", read_timeout: float = config.HTTP_RESULT_TIMEOUT,
              retries: int = config.HTTP_RETRIES) -> str:
        return self._request("GET", "/Popup.php", read_timeout=read_timeout, retries=retries, params={
            "page": name, "uid": 1, "data": data, "sessid": self.sessid, "Temp": int(time.time() * 1000)}).text

    def export(self, name: str, param: str | None = None) -> str:
        """Excel export of the last result of the session (SpreadsheetML text)."""
        params = {"page": name, "uid": 1, "lang": 1, "Temp": int(time.time() * 1000)}
        if param is not None:
            params["PARAM"] = param
        r = self._request("GET", "/xml/xmlopen.php", params=params)
        m = re.search(r"href='([^']+\.xls)'", r.text)
        if not m:
            raise SiteError(f"export {name}: no file link in {r.text[:200]!r}")
        return self._request("GET", f"/xml/{m.group(1)}").text

    def contracts(self, line_id: int, year_index: int) -> str:
        # few attempts: a page that hangs is skipped and requested again at the end of the pass
        return self.popup("SITE_C", f"<PARAM>{line_id};{year_index};</PARAM>", read_timeout=config.HTTP_CONTRACT_TIMEOUT,
                          retries=2)

    def get_bytes(self, path: str) -> bytes:
        return self._request("GET", path).content

    # -- high level ----------------------------------------------------------
    def query(self, report: config.Report, fields: list[tuple[str, str]], expect_group: list[str] | None = None,
              attempts: int = 3, allow_empty: bool = False,
              read_timeout: float = config.HTTP_RESULT_TIMEOUT) -> tuple[str, Grid]:
        """Run a report query and return (page text, grid).

        The view + popup pair depends on the session state; if the result is missing or
        does not have the expected grouping columns, the session is restarted and the
        query repeated.
        """
        last = None
        for attempt in range(1, attempts + 1):
            text = self.view(report.page, fields, read_timeout)
            if report.popup:
                text = self.popup(report.popup, read_timeout=read_timeout)
            grid = parse_grid(text)
            if grid is not None and not grid.records and allow_empty:
                return text, grid  # a filtered query (probe) can legitimately return nothing
            if grid is not None and grid.records:
                got = [c.caption for c in grid.group_columns] if report.popup else None
                if expect_group is None or got == expect_group:
                    return text, grid
                last = f"grouping {got} != {expect_group}"
            else:
                last = "no grid in the response"
            log.warning("%s %s: %s (attempt %d), restarting the session", report.key, fields[:3], last, attempt)
            time.sleep(5 * attempt)
            self.restart()
        raise SiteError(f"{report.key} {fields}: {last}")

    def form_for_year(self, report: config.Report, year_index: int,
                      extra: list[tuple[str, str]] | None = None) -> tuple[str, FormPage]:
        """The form after choosing a year: its checkbox lists are the classifiers of that year."""
        text = self.view(report.page, [("SITE_YEAR", year_index), *(extra or [])])
        return text, parse_form(text)
