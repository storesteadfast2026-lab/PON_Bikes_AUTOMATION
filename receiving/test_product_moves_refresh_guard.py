import hashlib
import os
import tempfile
from datetime import timedelta
from pathlib import Path
from types import SimpleNamespace

from django.test import SimpleTestCase
from django.utils import timezone

from receiving.views import _product_moves_local_refresh_is_stale


class ProductMovesRefreshGuardTests(SimpleTestCase):
    def _file(self, content=b"old-local", age_seconds=3600):
        temp = tempfile.NamedTemporaryFile(delete=False)
        temp.write(content)
        temp.close()
        path = Path(temp.name)
        ts = (timezone.now() - timedelta(seconds=age_seconds)).timestamp()
        os.utime(path, (ts, ts))
        self.addCleanup(lambda: path.unlink(missing_ok=True))
        return path

    def test_older_local_copy_cannot_replace_newer_manual_upload(self):
        path = self._file(b"old-local", age_seconds=7200)
        active = SimpleNamespace(
            source_path="manual upload",
            sha256=hashlib.sha256(b"new-upload").hexdigest(),
            imported_at=timezone.now() - timedelta(seconds=60),
        )
        self.assertTrue(_product_moves_local_refresh_is_stale(active, path, b"old-local", direct_source=False))

    def test_same_hash_is_not_blocked(self):
        content=b"same"
        path=self._file(content)
        active=SimpleNamespace(
            source_path="manual upload",
            sha256=hashlib.sha256(content).hexdigest(),
            imported_at=timezone.now(),
        )
        self.assertFalse(_product_moves_local_refresh_is_stale(active, path, content, direct_source=False))

    def test_direct_source_is_never_treated_as_local_fallback(self):
        path=self._file(b"direct", age_seconds=7200)
        active=SimpleNamespace(
            source_path="manual upload",
            sha256=hashlib.sha256(b"manual").hexdigest(),
            imported_at=timezone.now(),
        )
        self.assertFalse(_product_moves_local_refresh_is_stale(active, path, b"direct", direct_source=True))
