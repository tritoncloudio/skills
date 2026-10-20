import importlib.util
import sys
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "generate", Path(__file__).resolve().parent.parent / "scripts" / "generate.py"
)
generate = importlib.util.module_from_spec(spec)
sys.argv = sys.argv[:1]
spec.loader.exec_module(generate)


class SplitSections(unittest.TestCase):
    def test_splits_at_level_only(self):
        text = "### a\n\nbody a\n#### sub\n\n### b\nbody b\n"
        self.assertEqual(
            generate.split_sections(text, "###"),
            [("a", "body a\n#### sub"), ("b", "body b")],
        )


class SchemaType(unittest.TestCase):
    def test_ref_links_to_schemas(self):
        self.assertEqual(
            generate.schema_type({"$ref": "#/components/schemas/SandboxSpec"}),
            "[SandboxSpec](schemas.md#sandboxspec)",
        )

    def test_array_map_enum_format(self):
        self.assertEqual(generate.schema_type({"type": "array", "items": {"type": "string"}}),
                         "array of string")
        self.assertEqual(
            generate.schema_type({"type": "object", "additionalProperties": {"type": "string"}}),
            "map of string",
        )
        self.assertEqual(generate.schema_type({"type": "string", "enum": ["a", "b"]}),
                         "`a` \\| `b`")
        self.assertEqual(generate.schema_type({"type": "string", "format": "uuid"}),
                         "string (uuid)")

    def test_cell_escapes_pipes_and_newlines(self):
        self.assertEqual(generate.cell("a |\n b"), "a \\| b")


if __name__ == "__main__":
    unittest.main()
