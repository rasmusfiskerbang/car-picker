from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from car_picker.json_persistence import write_json_atomically


class JsonPersistenceTest(unittest.TestCase):
    def test_write_json_atomically_creates_parent_and_replaces_json(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "nested" / "record.json"

            write_json_atomically(target, {"message": "føtex", "count": 2})

            self.assertEqual(
                target.read_text(encoding="utf-8"),
                '{"message":"føtex","count":2}',
            )
            self.assertEqual(
                json.loads(target.read_text(encoding="utf-8")),
                {"message": "føtex", "count": 2},
            )


if __name__ == "__main__":
    unittest.main()
