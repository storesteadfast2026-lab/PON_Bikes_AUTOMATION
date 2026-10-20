"""Non-mutating UPStockSerial reconciliation regressions for historical Form1 order."""
from types import SimpleNamespace
from django.test import SimpleTestCase

from receiving.services import build_upstockserial_csv, reconcile_product_movements


class UpstockSerialLegacyOrderTests(SimpleTestCase):
    def test_legacy_location_sort_reorders_repeated_sku_without_changing_serial(self):
        # Recorded physical scan order: T4487, T4488, then T4486.
        # Historical Excel Form1 order: T4486, T4487, T4488.
        received = [
            SimpleNamespace(id=1, source_row=68, code="D690006045", long_code="", quantity=1, location="T4487"),
            SimpleNamespace(id=2, source_row=72, code="D690006045", long_code="", quantity=1, location="T4488"),
            SimpleNamespace(id=3, source_row=76, code="D690006045", long_code="", quantity=1, location="T4486"),
        ]
        movements = [
            {"product": "D690006045", "movement": str(movement)}
            for movement in (9476487, 9476488, 9476489)
        ]
        result = reconcile_product_movements(received, movements)
        self.assertTrue(result["ready"])
        self.assertEqual(
            [(item["movement"], item["serial_no"], item["location"]) for item in result["rows"]],
            [
                ("9476487", "76", "T4486"),
                ("9476488", "68", "T4487"),
                ("9476489", "72", "T4488"),
            ],
        )

    def test_second_observed_pallet_swap_is_corrected(self):
        received = [
            SimpleNamespace(id=1, source_row=100, code="D690006040", long_code="", quantity=1, location="T4498"),
            SimpleNamespace(id=2, source_row=101, code="D690006040", long_code="", quantity=1, location="T4496"),
        ]
        moves = [
            {"product": "D690006040", "movement": "9476451"},
            {"product": "D690006040", "movement": "9476453"},
        ]
        result = reconcile_product_movements(received, moves)
        self.assertTrue(result["ready"])
        self.assertEqual([r["location"] for r in result["rows"]], ["T4496", "T4498"])

    def test_long_code_primary_location_secondary_and_stable_tie(self):
        received = [
            SimpleNamespace(id=1, source_row=3, code="SKU0001", long_code="68-00002-1-123-4567", quantity=1, location="T4109"),
            SimpleNamespace(id=2, source_row=7, code="SKU0001", long_code="68-00001-1-123-4567", quantity=1, location="T4108"),
            SimpleNamespace(id=3, source_row=9, code="SKU0001", long_code="68-00001-1-123-4567", quantity=1, location="T4107"),
            SimpleNamespace(id=4, source_row=11, code="SKU0001", long_code="68-00001-1-123-4567", quantity=1, location="T4107"),
        ]
        movements = [{"product": "SKU0001", "movement": str(9478000+i)} for i in range(4)]
        result = reconcile_product_movements(received, movements)
        self.assertTrue(result["ready"])
        self.assertEqual([r["serial_no"] for r in result["rows"]], ["9", "11", "7", "3"])
        self.assertEqual([r["location"] for r in result["rows"]], ["T4107", "T4107", "T4108", "T4109"])

    def test_blank_long_codes_sort_last_when_mixed(self):
        received = [
            SimpleNamespace(id=1, source_row=2, code="BIKE01", long_code="", quantity=1, location="T4101"),
            SimpleNamespace(id=2, source_row=3, code="BIKE01", long_code="68-12345-1-123-4567", quantity=1, location="T4102"),
        ]
        result = reconcile_product_movements(received, [{"product": "BIKE01", "movement": "9479001"}, {"product": "BIKE01", "movement": "9479002"}])
        self.assertTrue(result["ready"])
        self.assertEqual([r["serial_no"] for r in result["rows"]], ["3", "2"])

    def test_mismatched_count_or_invalid_location_remains_blocked(self):
        received = [SimpleNamespace(id=1, source_row=1, code="BIKE01", long_code="", quantity=1, location="WRONG")]
        result = reconcile_product_movements(received, [{"product": "BIKE01", "movement": "9479001"}])
        self.assertFalse(result["ready"])
        self.assertTrue(result["issues"])

    def test_export_preserves_movement_order_and_existing_format(self):
        result = reconcile_product_movements([
            SimpleNamespace(id=1, source_row=16, code="BIKE01", long_code="", quantity=1, location="T4102"),
            SimpleNamespace(id=2, source_row=12, code="BIKE01", long_code="", quantity=1, location="T4101"),
        ], [{"product": "BIKE01", "movement": "9479002"}, {"product": "BIKE01", "movement": "9479001"}])
        self.assertTrue(result["ready"])
        self.assertEqual(build_upstockserial_csv(result["rows"]).decode("utf-8").splitlines(), [
            "Movement,serial_no,Loc", "   9479001,16,T4102", "   9479002,12,T4101",
        ])

    def test_historical_seku6363244_movements_serials_and_locations(self):
        # Original!A and Import!E:K, saved customer workbook SEKU6363244.
        sources = [
            (6, "T4217", "9253758"), (7, "T4217", "9253759"),
            (16, "T4219", "9253760"), (17, "T4219", "9253761"),
            (18, "T4219", "9253762"), (30, "T4221", "9253763"),
            (35, "T4222", "9253764"),
        ]
        lines = [SimpleNamespace(id=seq, source_row=seq, code="D673520765", long_code="", quantity=1, location=loc) for seq, loc, _ in sources]
        moves = [{"product": "D673520765", "movement": mv} for _, _, mv in sources]
        actual = reconcile_product_movements(lines, moves)
        self.assertTrue(actual["ready"])
        self.assertEqual([(r["movement"], r["serial_no"], r["location"]) for r in actual["rows"]],
                         [(mv, str(seq), loc) for seq, loc, mv in sources])

    def test_historical_oneu2096348_movements_serials_and_locations(self):
        sources = [(92, "9424896"), (104, "9424897")]
        lines = [SimpleNamespace(id=seq, source_row=seq, code="0M0S5GDI1C51", long_code="", quantity=1, location="T4349") for seq, _ in sources]
        moves = [{"product": "0M0S5GDI1C51", "movement": mv} for _, mv in sources]
        actual = reconcile_product_movements(lines, moves)
        self.assertTrue(actual["ready"])
        self.assertEqual([(r["movement"], r["serial_no"], r["location"]) for r in actual["rows"]],
                         [(mv, str(seq), "T4349") for seq, mv in sources])

    def test_historical_hlxu8851552_movements_serials_and_locations(self):
        sources = [(102, "9150049"), (103, "9150066"), (105, "9150067")]
        lines = [SimpleNamespace(id=seq, source_row=seq, code="D680511002", long_code="", quantity=1, location="T4139") for seq, _ in sources]
        moves = [{"product": "D680511002", "movement": mv} for seq, mv in sources]
        actual = reconcile_product_movements(lines, moves)
        self.assertTrue(actual["ready"])
        self.assertEqual([(r["movement"], r["serial_no"], r["location"]) for r in actual["rows"]],
                         [(mv, str(seq), "T4139") for seq, mv in sources])
