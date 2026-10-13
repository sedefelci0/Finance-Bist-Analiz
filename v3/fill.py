"""v3 ham finansal tablo dolumu — kaynaktan bağımsız iskelet.

Bu modül HİÇBİR kaynağa istek atmaz. Gerçek bir sağlayıcı (`StatementProvider`)
ancak kaynak kararı verildikten sonra yazılacak (bkz. docs/scoring-v3.md §9,
"Ana kaynak kararı: BEKLEMEDE"). Burada yalnızca şunlar var:

- `StatementProvider`: tek bir isteği BİR KEZ deneyen kaynak arayüzü.
- `FillStore`: çekilen ham cevabı saklayan ve "bu istek zaten tamam mı?"
  sorusunu cevaplayan depo arayüzü (Neon v3-dev branch'i için ayrıca yazılacak).
- `run_fill`: hız sınırı, tekrar deneme, kaldığı yerden devam ve önbellek
  mantığı. Ham cevap olduğu gibi saklanır, hiçbir hesaplama yapılmaz.

0 kalem kuralı (kullanıcı kararı, 13 Ekim): kaynak 0 kalem dönerse bu hata
gibi tekrar denenir; `max_attempts` denemeden sonra hâlâ 0 ise istek
"kaynakta_yok" diye işaretlenir ve dolum bir sonraki istekle devam eder.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Iterable, Literal, Protocol

Status = Literal["ok", "kaynakta_yok", "hata"]


@dataclass(frozen=True)
class FetchRequest:
    """Tek bir kaynak isteği: bir hisse, bir tablo grubu, bir dönem seti."""

    ticker: str
    group: str  # kaynağa özgü tablo grubu (ör. sanayi / konsolide banka)
    periods: tuple[tuple[int, int], ...]  # (yıl, ay) çiftleri


@dataclass(frozen=True)
class RawItem:
    """Kaynağın bir kalemi, bir dönem için, olduğu gibi."""

    item_code: str
    item_name: str
    period: tuple[int, int]
    value: float | None


@dataclass(frozen=True)
class RawResponse:
    """Sağlayıcının tek bir denemede döndürdüğü ham cevap."""

    items: tuple[RawItem, ...]
    payload: Any  # kaynağın cevabı, olduğu gibi (saklanır, yorumlanmaz)


class TransientError(Exception):
    """Zaman aşımı, bağlantı hatası, 5xx gibi tekrar denemeye değer hatalar."""


class StatementProvider(Protocol):
    name: str

    def fetch(self, request: FetchRequest) -> RawResponse:
        """İsteği bir kez dener. Geçici hatada `TransientError` fırlatır."""
        ...


@dataclass
class FetchResult:
    request: FetchRequest
    source: str
    status: Status
    attempts: int
    fetched_at: datetime
    items: tuple[RawItem, ...] = ()
    payload: Any = None
    error: str | None = None


class FillStore(Protocol):
    def is_done(self, source: str, request: FetchRequest) -> bool:
        """İstek daha önce 'ok' ya da 'kaynakta_yok' ile tamamlandıysa True (önbellek / devam)."""
        ...

    def save(self, result: FetchResult) -> None:
        ...


@dataclass
class InMemoryStore:
    """Testler için depo. Gerçek depo Neon v3-dev branch'ine yazacak."""

    results: list[FetchResult] = field(default_factory=list)

    def is_done(self, source: str, request: FetchRequest) -> bool:
        return any(r.source == source and r.request == request and r.status != "hata" for r in self.results)

    def save(self, result: FetchResult) -> None:
        self.results.append(result)


def order_by_priority(tickers: Iterable[str], priority: set[str]) -> list[str]:
    """Öncelikli hisseler (BIST100) önce, kalanlar sonra; her grup alfabetik."""
    tickers = sorted(set(tickers))
    return [t for t in tickers if t in priority] + [t for t in tickers if t not in priority]


@dataclass
class _RateLimiter:
    min_interval: float
    clock: Callable[[], float]
    sleep: Callable[[float], None]
    _last: float | None = None

    def wait(self) -> None:
        if self._last is not None:
            remaining = self.min_interval - (self.clock() - self._last)
            if remaining > 0:
                self.sleep(remaining)
        self._last = self.clock()


def run_fill(
    provider: StatementProvider,
    store: FillStore,
    requests: Iterable[FetchRequest],
    *,
    min_interval: float = 5.0,
    max_attempts: int = 3,
    backoff: tuple[float, ...] = (10.0, 30.0, 60.0),
    sleep: Callable[[float], None] = time.sleep,
    clock: Callable[[], float] = time.monotonic,
    now: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
) -> dict[str, int]:
    """İstekleri sırayla işler; özet sayıları döner (işlenen, atlanan, ok, kaynakta_yok, hata)."""
    limiter = _RateLimiter(min_interval, clock, sleep)
    summary = {"islenen": 0, "atlanan": 0, "ok": 0, "kaynakta_yok": 0, "hata": 0}

    for request in requests:
        if store.is_done(provider.name, request):
            summary["atlanan"] += 1
            continue
        summary["islenen"] += 1

        response: RawResponse | None = None
        error: str | None = None
        attempts = 0
        for attempts in range(1, max_attempts + 1):
            limiter.wait()
            try:
                response = provider.fetch(request)
                error = None
            except TransientError as exc:
                response, error = None, f"{type(exc).__name__}: {exc}"
            if response is not None and response.items:
                break
            if attempts < max_attempts:
                sleep(backoff[min(attempts - 1, len(backoff) - 1)])

        if response is not None and response.items:
            status: Status = "ok"
        elif response is not None:
            status = "kaynakta_yok"  # cevap geldi ama 0 kalem, tüm denemelerde
        else:
            status = "hata"
        store.save(FetchResult(request, provider.name, status, attempts, now(),
                               response.items if response else (), response.payload if response else None, error))
        summary[status] += 1

    return summary
