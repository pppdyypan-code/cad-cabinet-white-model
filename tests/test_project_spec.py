import copy
import json
from pathlib import Path
import sys
import unittest

SKILL = Path(__file__).resolve().parents[1]/"skills/cad-cabinet-white-model"
sys.path.insert(0, str(SKILL/"scripts"))
from project_spec import geometry_key, validate


class ProjectContractTests(unittest.TestCase):
    def setUp(self):
        self.project=json.loads((SKILL/"assets/example-project.json").read_text())

    def test_example_is_consistent(self):
        self.assertIs(validate(self.project),self.project)

    def test_conflicting_column_sum_is_rejected(self):
        self.project["components"][0]["columns"][0]["width_mm"]+=20
        with self.assertRaisesRegex(ValueError,"column widths"):
            validate(self.project)

    def test_drawer_rows_must_match_height(self):
        self.project["components"][1]["columns"][0]["rows_mm"]=[250,250]
        with self.assertRaisesRegex(ValueError,"row heights"):
            validate(self.project)

    def test_camera_change_does_not_invalidate_geometry_identity(self):
        original=geometry_key(self.project)
        self.project["cameras"][0]["position_mm"][2]=1200
        self.assertEqual(original,geometry_key(self.project))
        self.project["components"][0]["depth_mm"]=570
        self.assertNotEqual(original,geometry_key(self.project))

    def test_unsafe_output_identifier_is_rejected(self):
        self.project["cameras"][0]["id"]="../../outside"
        with self.assertRaisesRegex(ValueError,"identifier"):
            validate(self.project)

    def test_nonfinite_coordinates_rejected(self):
        self.project["cameras"][0]["position_mm"][0]=float("nan")
        with self.assertRaisesRegex(ValueError,"non-finite"):
            validate(self.project)

    def test_duplicate_camera_rejected(self):
        self.project["cameras"].append(copy.deepcopy(self.project["cameras"][0]))
        with self.assertRaisesRegex(ValueError,"Duplicate camera"):
            validate(self.project)

    def test_handle_length_cannot_exceed_front(self):
        self.project["components"][1]["columns"][0]["handle"]["length_mm"]=600
        with self.assertRaisesRegex(ValueError,"Handle is longer"):
            validate(self.project)

    def test_existing_mode_can_reference_an_imported_scene(self):
        validate({"schema_version":1,"units":"mm","mode":"existing","cameras":self.project["cameras"]})


if __name__=="__main__":
    unittest.main()
