from django.test import SimpleTestCase

from receiving.services import build_upstockserial_csv


class UpstockSerialNoEmptyRowsTests(SimpleTestCase):
    def test_only_real_rows_are_written_and_movement_keeps_ten_characters(self):
        rows = [
            {"movement": "9451414", "serial_no": "47", "location": "T4401"},
            {"movement": "9451415", "serial_no": "14", "location": "T4394"},
        ]
        content = build_upstockserial_csv(rows)
        lines = content.decode("utf-8").splitlines()

        self.assertEqual(
            lines,
            [
                "Movement,serial_no,Loc",
                "   9451414,47,T4401",
                "   9451415,14,T4394",
            ],
        )
        self.assertNotIn(",,", content.decode("utf-8"))

    def test_empty_input_writes_header_only(self):
        content = build_upstockserial_csv([])
        self.assertEqual(content.decode("utf-8"), "Movement,serial_no,Loc\r\n")

    def test_max_rows_is_still_a_safety_limit(self):
        rows = [
            {"movement": str(9451000 + i), "serial_no": str(i), "location": "T4401"}
            for i in range(2)
        ]
        with self.assertRaises(ValueError):
            build_upstockserial_csv(rows, max_rows=1)
