from types import SimpleNamespace

from django.core.files.base import ContentFile
from django.test import SimpleTestCase

from receiving.services import build_upstockserial_csv
from receiving.views import _upstock_export_has_10_char_movements


class UpstockSerialCachePaddingTests(SimpleTestCase):
    def test_service_output_has_ten_raw_movement_characters(self):
        content = build_upstockserial_csv(
            [{"movement": "9450119", "serial_no": "2", "location": "T4377"}],
            max_rows=1,
        )
        movement = content.split(b"\r\n")[1].split(b",", 1)[0]
        self.assertEqual(movement, b"   9450119")
        self.assertEqual(len(movement), 10)

    def test_old_seven_character_cache_is_rejected(self):
        export = SimpleNamespace(
            file=ContentFile(
                b"Movement,serial_no,Loc\r\n9450119,2,T4377\r\n",
                name="old-upstock.csv",
            ),
            row_count=1,
        )
        self.assertFalse(_upstock_export_has_10_char_movements(export))

    def test_ten_character_cache_is_reused(self):
        export = SimpleNamespace(
            file=ContentFile(
                b"Movement,serial_no,Loc\r\n   9450119,2,T4377\r\n",
                name="new-upstock.csv",
            ),
            row_count=1,
        )
        self.assertTrue(_upstock_export_has_10_char_movements(export))
