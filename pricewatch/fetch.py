"""Polite HTTP: robots.txt, a delay per host, retries with backoff, identifiable user agent."""
import time, threading, urllib.request, urllib.error, urllib.robotparser
from urllib.parse import urlsplit

UA = "price-watch/0.1 (+https://github.com/bitexact-labs/price-watch)"


class Fetcher:
    def __init__(self, delay=0.5, retries=3, timeout=20, opener=None):
        self.delay, self.retries, self.timeout = delay, retries, timeout
        self._open = opener or (lambda req, timeout: urllib.request.urlopen(req, timeout=timeout))
        self._last, self._lock, self._robots = {}, threading.Lock(), {}
        self.requests = 0

    def allowed(self, url):
        host = "{0.scheme}://{0.netloc}".format(urlsplit(url))
        if host not in self._robots:
            rp = urllib.robotparser.RobotFileParser()
            try:
                with self._open(urllib.request.Request(host + "/robots.txt", headers={"User-Agent": UA}), self.timeout) as r:
                    rp.parse(r.read().decode("utf-8", "replace").splitlines())
            except urllib.error.HTTPError as e:
                rp.parse([] if e.code in (404, 410) else ["User-agent: *", "Disallow: /"])   # no robots.txt = allowed
            except OSError:
                rp.parse([])
            self._robots[host] = rp
        return self._robots[host].can_fetch(UA, url)

    def _wait(self, host):
        with self._lock:
            now = time.monotonic()
            t = max(now, self._last.get(host, 0) + self.delay)
            self._last[host] = t
        time.sleep(max(0, t - now))

    def get(self, url):
        if not self.allowed(url):
            raise PermissionError(f"robots.txt disallows {url}")
        host = urlsplit(url).netloc
        for attempt in range(self.retries + 1):
            self._wait(host)
            try:
                self.requests += 1
                with self._open(urllib.request.Request(url, headers={"User-Agent": UA}), self.timeout) as r:
                    return r.read().decode("utf-8", "replace")
            except urllib.error.HTTPError as e:
                if e.code not in (429, 500, 502, 503, 504) or attempt == self.retries:
                    raise
            except OSError:
                if attempt == self.retries:
                    raise
            time.sleep(min(30, 2 ** attempt))
