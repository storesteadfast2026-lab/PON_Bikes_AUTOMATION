import io
from types import SimpleNamespace

from django.test import SimpleTestCase

from receiving.views import _upstock_export_has_legacy_blank_padding


class _FakeFile:
    def __init__(self, content):
        self._content = content
        self._stream = None

    def open(self, mode="rb"):
        self._stream = io.BytesIO(self._content)
        return self

    def read(self):
        return self._stream.read()

    def close(self):
        if self._stream is not None:
            self._stream.close()


class UpstockSerialLegacyPaddingCacheTests(SimpleTestCase):
    def test_detects_legacy_blank_padding(self):
        export = SimpleNamespace(
            file=_FakeFile(
                b"Movement,serial_no,Loc\r\n"
                b"   9451414,47,T4401\r\n"
                b",,\r\n"
                b",,\r\n"
            )
        )
        self.assertTrue(_upstock_export_has_legacy_blank_padding(export))

    def test_compact_export_is_not_invalidated(self):
        export = SimpleNamespace(
            file=_FakeFile(
                b"Movement,serial_no,Loc\r\n"
                b"   9451414,47,T4401\r\n"
                b"   9451415,14,T4394\r\n"
            )
        )
        self.assertFalse(_upstock_export_has_legacy_blank_padding(export))

    def test_missing_export_file_is_not_misclassified(self):
        self.assertFalse(_upstock_export_has_legacy_blank_padding(None))
        self.assertFalse(_upstock_export_has_legacy_blank_padding(SimpleNamespace(file=None)))
