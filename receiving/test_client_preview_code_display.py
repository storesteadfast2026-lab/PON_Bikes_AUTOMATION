from pathlib import Path
from django.conf import settings
from django.test import SimpleTestCase

class ClientPreviewCodeDisplayPatchTests(SimpleTestCase):
    def test_marker_and_safe_display_logic_present(self):
        p=Path(settings.BASE_DIR)/"receiving"/"templates"/"receiving"/"batch_preview.html"
        t=p.read_text(encoding="utf-8")
        self.assertIn("PON_CLIENT_PREVIEW_CODE_DISPLAY_1008.1134",t)
        self.assertIn("data-source-code-not-provided",t)
        self.assertIn("x.code.toUpperCase()===x.longcode.toUpperCase()",t)
        self.assertIn("Internal Code/LongCode association is retained.",t)

    def test_display_patch_has_no_server_write(self):
        p=Path(settings.BASE_DIR)/"receiving"/"templates"/"receiving"/"batch_preview.html"
        t=p.read_text(encoding="utf-8")
        b=t[t.index("PON_CLIENT_PREVIEW_CODE_DISPLAY_1008.1134"):]
        self.assertNotIn("fetch(",b)
        self.assertNotIn("XMLHttpRequest",b)
        self.assertNotIn("form.submit",b)
        self.assertNotIn(".value=",b)
