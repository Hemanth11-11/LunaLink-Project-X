from lunalink.config import default_mission_config
from lunalink.exporters import write_scenario_exports


def test_write_scenario_exports(tmp_path):
    paths = write_scenario_exports(default_mission_config(), tmp_path)

    assert set(paths) == {
        "gmat",
        "orekit",
        "external_validation_recipe",
        "external_comparison_template",
    }
    assert (tmp_path / "LunaLink_GMAT_scenario.script").exists()
    assert (tmp_path / "LunaLink_Orekit_scenario.json").exists()
    assert (tmp_path / "LunaLink_external_validation_recipe.md").exists()
    assert (tmp_path / "LunaLink_external_comparison_template.csv").exists()
    assert "LunaLink.SMA" in (tmp_path / "LunaLink_GMAT_scenario.script").read_text(
        encoding="utf-8"
    )
