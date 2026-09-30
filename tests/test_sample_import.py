import sys
import unittest
from collections import Counter
from pathlib import Path
from types import SimpleNamespace


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from receiving.services import compare_lines, parse_workbook, suggest_mapping


class SampleImportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client_file = PROJECT_ROOT / "sample_data" / "TCNU4108637.xlsx"
        cls.received_file = PROJECT_ROOT / "sample_data" / "TCNU4108637 PON CON40 15-09-26.xlsx"
        if not cls.client_file.exists() or not cls.received_file.exists():
            raise unittest.SkipTest("Sample files are not present.")

    def test_client_manifest_detects_sku_quantity_and_coloured_rows(self):
        mapping = suggest_mapping(self.client_file, "CLIENT")
        self.assertEqual(mapping["code_column"], "D")
        self.assertEqual(mapping["quantity_column"], "G")
        self.assertEqual(mapping["description_column"], "E")
        self.assertTrue(mapping["coloured_rows_only"])

        rows, errors = parse_workbook(self.client_file, mapping)
        self.assertEqual(errors, [])
        self.assertEqual(len(rows), 26)
        self.assertEqual(sum(row["quantity"] for row in rows), 78)

    def test_first_scan_assigns_three_bikes_to_each_location(self):
        mapping = suggest_mapping(self.received_file, "RECEIVED")
        rows, errors = parse_workbook(self.received_file, mapping)
        self.assertEqual(errors, [])
        self.assertEqual(len(rows), 78)
        counts = Counter(row["location"] for row in rows)
        self.assertEqual(len(counts), 26)
        self.assertTrue(all(quantity == 3 for quantity in counts.values()))

    def test_real_samples_match_exactly(self):
        client_rows, _ = parse_workbook(self.client_file, suggest_mapping(self.client_file, "CLIENT"))
        received_rows, _ = parse_workbook(self.received_file, suggest_mapping(self.received_file, "RECEIVED"))
        expected = [SimpleNamespace(code=row["code"], quantity=row["quantity"]) for row in client_rows]
        received = [SimpleNamespace(code=row["code"], quantity=row["quantity"]) for row in received_rows]
        result = compare_lines(expected, received)
        self.assertEqual(sum(row["expected"] for row in result), 78)
        self.assertEqual(sum(row["received"] for row in result), 78)
        self.assertTrue(all(row["status"] == "MATCH" for row in result))


if __name__ == "__main__":
    unittest.main()
