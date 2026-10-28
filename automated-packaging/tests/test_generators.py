"""What a MoveApps appspec becomes: the CWL CommandLineTool, its Dockerfile and the job
file - for every setting type the appspec knows."""

import yaml

from moveapps_cwl_packager.generators import generate_cwl, generate_dockerfile_content, generate_inputs_yaml
from moveapps_cwl_packager.packager import parse_github_url, repo_name_to_image

SETTINGS = [
    {"id": "maxspeed", "type": "DOUBLE", "defaultValue": "20.5", "description": "km/h"},
    {"id": "window", "type": "INTEGER", "defaultValue": "5"},
    {"id": "strict", "type": "CHECKBOX", "defaultValue": "false"},
    {"id": "keep", "type": "BOOLEAN", "defaultValue": True},
    {"id": "unit", "type": "RADIOBUTTON", "defaultValue": "m"},
    {"id": "start", "type": "TIMESTAMP", "defaultValue": ""},
    {"id": "label", "type": "STRING"},
    {"id": "future", "type": "SOMETHING_NEW", "defaultValue": "x"},
]

DOCKERFILE = generate_dockerfile_content("moveapps-r-wrapper:latest", "https://raw.example/owner/repo/main")


def cwl(settings: list[dict] = SETTINGS) -> dict:
    return yaml.safe_load(generate_cwl("remove-outliers", settings, DOCKERFILE))


def test_the_tool_is_a_cwl_v1_2_command_line_tool_running_the_wrapper() -> None:
    doc = cwl()
    assert (doc["cwlVersion"], doc["class"]) == ("v1.2", "CommandLineTool")
    assert doc["baseCommand"] == ["/home/moveapps/co-pilot-r/cwl-wrapper.sh"]
    assert doc["requirements"]["DockerRequirement"] == {"dockerFile": DOCKERFILE, "dockerImageId": "remove-outliers"}
    assert set(doc["outputs"]) == {"output_rds", "error_log", "artifacts"}


def test_the_rds_input_comes_first_then_every_setting_in_appspec_order() -> None:
    inputs = cwl()["inputs"]
    assert list(inputs) == ["input_rds", *(s["id"] for s in SETTINGS)]
    assert inputs["input_rds"]["type"] == "File"


def test_every_setting_type_maps_to_an_optional_cwl_type() -> None:
    types = {name: spec["type"] for name, spec in cwl()["inputs"].items() if name != "input_rds"}
    assert types == {
        "maxspeed": "double?",
        "window": "int?",
        "strict": "boolean?",
        "keep": "boolean?",
        "unit": "string?",
        "start": "string?",
        "label": "string?",
        # an appspec type this packager doesn't know yet is still packaged, as text
        "future": "string?",
    }


def test_defaults_are_typed_and_an_empty_one_is_left_out() -> None:
    inputs = cwl()["inputs"]
    assert inputs["maxspeed"]["default"] == 20.5
    assert inputs["window"]["default"] == 5
    assert inputs["strict"]["default"] is False
    assert inputs["keep"]["default"] is True
    assert inputs["unit"]["default"] == "m"
    assert "default" not in inputs["start"]
    assert "default" not in inputs["label"]
    assert inputs["maxspeed"]["doc"] == "km/h"


def test_the_app_configuration_hands_every_setting_to_the_r_function() -> None:
    [listing] = cwl()["requirements"]["InitialWorkDirRequirement"]["listing"]
    assert listing["entryname"] == "app-configuration.json"
    for setting in SETTINGS:
        assert f'"{setting["id"]}": inputs["{setting["id"]}"]' in listing["entry"]


def test_an_app_without_settings_still_makes_a_valid_tool() -> None:
    doc = cwl([])
    assert list(doc["inputs"]) == ["input_rds"]
    [listing] = doc["requirements"]["InitialWorkDirRequirement"]["listing"]
    assert "JSON.stringify" in listing["entry"]


def test_setting_ids_that_are_no_js_identifiers_make_a_valid_expression() -> None:
    [listing] = cwl([{"id": "loc.err", "type": "DOUBLE"}, {"id": "auxiliary-file-a", "type": "USER_FILE"}])[
        "requirements"
    ]["InitialWorkDirRequirement"]["listing"]
    assert '"loc.err": inputs["loc.err"]' in listing["entry"]
    assert '"auxiliary-file-a": inputs["auxiliary-file-a"]' in listing["entry"]


def test_umlauts_in_a_description_stay_readable() -> None:
    text = generate_cwl("app", [{"id": "x", "type": "STRING", "description": "Höchstgeschwindigkeit"}], DOCKERFILE)
    assert "Höchstgeschwindigkeit" in text


def test_the_dockerfile_installs_only_the_r_packages_the_app_needs() -> None:
    plain = generate_dockerfile_content("wrapper:1", "https://raw.example/o/r/main")
    assert plain.startswith("FROM --platform=linux/amd64 wrapper:1")
    assert "install.packages" not in plain
    assert "https://raw.example/o/r/main/RFunction.R" in plain
    # optional in a MoveApps repo, and CWL writes the configuration from the inputs anyway
    assert "app-configuration.json" not in plain

    with_packages = generate_dockerfile_content("wrapper:1", "https://raw.example/o/r/main", ["sf", "move2"])
    assert 'c("sf", "move2")' in with_packages


def test_r_packages_come_from_the_wrapper_images_pinned_repository_and_a_failed_one_fails_the_build() -> None:
    dockerfile = generate_dockerfile_content("wrapper:1", "https://raw.example/o/r/main", ["ctmm"])
    assert "repos" not in dockerfile
    assert "quit(status = 1)" in dockerfile


def test_the_job_file_takes_the_appspec_defaults_typed() -> None:
    job = yaml.safe_load(generate_inputs_yaml(SETTINGS))
    assert job["input_rds"] == {"class": "File", "path": "/path/to/your/input.rds"}
    assert (job["maxspeed"], job["window"], job["strict"], job["keep"]) == (20.5, 5, False, True)


def test_a_setting_without_a_default_is_left_null_and_says_so() -> None:
    text = generate_inputs_yaml(SETTINGS)
    job = yaml.safe_load(text)
    # an empty defaultValue counts as none - no made-up value that would run silently
    assert job["label"] is None and job["start"] is None
    assert "label: null  # string, no default in appspec.json - set a value" in text


def test_github_urls_are_read_in_their_usual_spellings() -> None:
    for url in (
        "https://github.com/movestore/RemoveOutliers",
        "https://github.com/movestore/RemoveOutliers/",
        "https://github.com/movestore/RemoveOutliers.git",
        "  http://github.com/movestore/RemoveOutliers  ",
    ):
        assert parse_github_url(url) == ("movestore", "RemoveOutliers"), url
    assert repo_name_to_image("Remove_Outliers") == "remove-outliers"
