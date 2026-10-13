"""v3.fill iskeleti — sahte sağlayıcıyla; gerçek istek yok."""
import unittest
from datetime import datetime, timezone

from v3.fill import (FetchRequest, InMemoryStore, RawItem, RawResponse, TransientError,
                     order_by_priority, run_fill)

P = ((2026, 6), (2026, 3), (2025, 12), (2025, 9))
ITEM = RawItem("1A", "Dönen Varlıklar", (2026, 6), 1.0)


class FakeProvider:
    """Her hisse için önceden yazılmış cevap dizisi döner: 'ok', 'bos' (0 kalem) ya da 'timeout'."""

    name = "sahte"

    def __init__(self, script):
        self.script = {k: list(v) for k, v in script.items()}
        self.calls = []

    def fetch(self, request):
        self.calls.append(request.ticker)
        step = self.script[request.ticker].pop(0)
        if step == "timeout":
            raise TransientError("zaman aşımı")
        if step == "bos":
            return RawResponse(items=(), payload={"value": []})
        return RawResponse(items=(ITEM,), payload={"value": ["..."]})


class FakeClock:
    def __init__(self):
        self.t = 0.0
        self.sleeps = []

    def clock(self):
        return self.t

    def sleep(self, s):
        self.sleeps.append(s)
        self.t += s


def run(provider, store, tickers, clock=None):
    clock = clock or FakeClock()
    reqs = [FetchRequest(t, "XI_29", P) for t in tickers]
    return run_fill(provider, store, reqs, sleep=clock.sleep, clock=clock.clock,
                    now=lambda: datetime(2026, 10, 13, tzinfo=timezone.utc)), clock


class TestRunFill(unittest.TestCase):
    def test_ok_first_try(self):
        store = InMemoryStore()
        summary, _ = run(FakeProvider({"AAA": ["ok"]}), store, ["AAA"])
        self.assertEqual(summary["ok"], 1)
        self.assertEqual(store.results[0].attempts, 1)
        self.assertEqual(store.results[0].payload, {"value": ["..."]})  # ham cevap olduğu gibi

    def test_timeout_then_ok_retries(self):
        store = InMemoryStore()
        summary, clock = run(FakeProvider({"AAA": ["timeout", "timeout", "ok"]}), store, ["AAA"])
        self.assertEqual(summary["ok"], 1)
        self.assertEqual(store.results[0].attempts, 3)
        self.assertIn(10.0, clock.sleeps)  # ilk geri çekilme
        self.assertIn(30.0, clock.sleeps)

    def test_zero_items_three_times_marks_kaynakta_yok_and_continues(self):
        store = InMemoryStore()
        provider = FakeProvider({"AAA": ["bos", "bos", "bos"], "BBB": ["ok"]})
        summary, _ = run(provider, store, ["AAA", "BBB"])
        self.assertEqual(summary, {"islenen": 2, "atlanan": 0, "ok": 1, "kaynakta_yok": 1, "hata": 0})
        self.assertEqual(store.results[0].status, "kaynakta_yok")
        self.assertEqual(store.results[0].attempts, 3)
        self.assertEqual(provider.calls, ["AAA", "AAA", "AAA", "BBB"])

    def test_all_timeouts_marks_hata(self):
        store = InMemoryStore()
        summary, _ = run(FakeProvider({"AAA": ["timeout"] * 3}), store, ["AAA"])
        self.assertEqual(summary["hata"], 1)
        self.assertIn("zaman aşımı", store.results[0].error)

    def test_resume_skips_done_and_retries_failed(self):
        store = InMemoryStore()
        run(FakeProvider({"AAA": ["ok"], "BBB": ["timeout"] * 3, "CCC": ["bos"] * 3}), store, ["AAA", "BBB", "CCC"])
        provider = FakeProvider({"BBB": ["ok"]})
        summary, _ = run(provider, store, ["AAA", "BBB", "CCC"])
        self.assertEqual(provider.calls, ["BBB"])  # ok ve kaynakta_yok önbellekten atlanır, hata tekrar denenir
        self.assertEqual(summary["atlanan"], 2)

    def test_rate_limit_min_interval(self):
        store = InMemoryStore()
        clock = FakeClock()
        run(FakeProvider({"AAA": ["ok"], "BBB": ["ok"]}), store, ["AAA", "BBB"], clock)
        self.assertEqual(clock.sleeps, [5.0])  # iki istek arasında en az 5 sn


class TestPriority(unittest.TestCase):
    def test_bist100_first_then_rest_alphabetical(self):
        self.assertEqual(order_by_priority(["ZZZ", "AAA", "MMM", "BBB"], {"MMM", "ZZZ"}),
                         ["MMM", "ZZZ", "AAA", "BBB"])


if __name__ == "__main__":
    unittest.main()
