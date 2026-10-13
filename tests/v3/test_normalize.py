"""v3.normalize — sahte TÜFE serisiyle (gerçek değil) ve Faz 0 ASELS rakamlarıyla."""
import os
import tempfile
import unittest
from datetime import date

from v3.normalize import MissingCPIError, cpi_factor, load_cpi, to_base, ttm_cumulative

# SAHTE endeks — yalnızca matematiği test eder, gerçek TÜFE değildir.
FAKE_CPI = {(2025, 12): 100.0, (2026, 3): 110.0, (2026, 6): 117.76}


class TestToBase(unittest.TestCase):
    def test_factor_and_conversion(self):
        self.assertAlmostEqual(cpi_factor(date(2025, 12, 31), date(2026, 6, 30), FAKE_CPI), 1.1776)
        self.assertAlmostEqual(to_base(1000.0, date(2025, 12, 31), date(2026, 6, 30), FAKE_CPI), 1177.6)

    def test_same_date_and_non_tms29_unchanged(self):
        self.assertEqual(to_base(5.0, date(2026, 6, 30), date(2026, 6, 30), FAKE_CPI), 5.0)
        self.assertEqual(to_base(5.0, date(2025, 12, 31), date(2026, 6, 30), FAKE_CPI, apply_tms29=False), 5.0)
        self.assertIsNone(to_base(None, date(2025, 12, 31), date(2026, 6, 30), FAKE_CPI))

    def test_missing_month_raises(self):
        with self.assertRaises(MissingCPIError):
            to_base(1.0, date(2024, 12, 31), date(2026, 6, 30), FAKE_CPI)


class TestTTM(unittest.TestCase):
    def test_asels_2026h1_revenue(self):
        # Faz 0: İş Yatırım rakamları, üçü de Haziran 2026 TL'si (bin TL değil, TL)
        ttm = ttm_cumulative(annual_prev=212_489_200_000, cum_current=88_494_252_000,
                             cum_prev_same_month=70_956_004_000, month=6)
        self.assertEqual(ttm, 230_027_448_000)

    def test_year_end_is_annual(self):
        self.assertEqual(ttm_cumulative(1.0, 7.0, 3.0, 12), 7.0)

    def test_missing_part_is_none(self):
        self.assertIsNone(ttm_cumulative(None, 7.0, 3.0, 6))


class TestLoadCPI(unittest.TestCase):
    def _write(self, text):
        fd, path = tempfile.mkstemp(suffix=".csv")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
        self.addCleanup(os.remove, path)
        return path

    def test_reads_rows(self):
        p = self._write("ay,endeks,kaynak\n2026-06,117.76,https://ornek\n2025-12,100,https://ornek\n")
        self.assertEqual(load_cpi(p), {(2026, 6): 117.76, (2025, 12): 100.0})

    def test_rejects_missing_source_and_duplicates(self):
        with self.assertRaises(ValueError):
            load_cpi(self._write("ay,endeks,kaynak\n2026-06,117.76,\n"))
        with self.assertRaises(ValueError):
            load_cpi(self._write("ay,endeks,kaynak\n2026-06,1,x\n2026-06,2,x\n"))


if __name__ == "__main__":
    unittest.main()
