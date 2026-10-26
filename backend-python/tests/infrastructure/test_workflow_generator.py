import yaml

from app.infrastructure.cwl.workflow_generator import (
    PortSpec,
    build_workflow_document,
    generate_workflow_inputs_yaml,
)

THIN = PortSpec(name="Thin Data", file_inputs={"input_rds": "File"}, file_outputs={"output_rds": "File"})
OUTLIERS = PortSpec(name="Remove Outliers", file_inputs={"input_rds": "File"}, file_outputs={"output_rds": "File"})
MERGE = PortSpec(name="Merge", file_inputs={"tracks": "File[]"}, file_outputs={"merged": "File"})


def node(node_id: str, component_id: str) -> dict:
    return {"id": node_id, "data": {"componentId": component_id, "parameterValues": {}}}


def edge(source: str, target: str) -> dict:
    return {"source": source, "target": target, "sourceHandle": "output_rds", "targetHandle": "input_rds"}


def test_only_unwired_inputs_become_job_entries() -> None:
    doc = build_workflow_document(
        "Thin and clean",
        [node("a", "thin"), node("b", "outliers")],
        [edge("a", "b")],
        {"thin": THIN, "outliers": OUTLIERS},
    )
    job = yaml.safe_load(generate_workflow_inputs_yaml("Thin and clean", doc))

    # the wired input of Remove Outliers is fed by Thin Data - only Thin Data's is open
    assert job == {"step_thin_data__input_rds": {"class": "File", "path": "/path/to/input_rds"}}
    # and it matches the .cwl's own inputs exactly
    assert set(job) == set(doc["inputs"])


def test_array_input_gets_a_list_of_files() -> None:
    doc = build_workflow_document("Merge it", [node("m", "merge")], [], {"merge": MERGE})
    job = yaml.safe_load(generate_workflow_inputs_yaml("Merge it", doc))
    assert job == {"step_merge__tracks": [{"class": "File", "path": "/path/to/tracks"}]}


def test_fully_wired_workflow_yields_an_empty_job() -> None:
    doc = {"inputs": {}}
    text = generate_workflow_inputs_yaml("Closed", doc)
    assert yaml.safe_load(text) == {}
    assert "needs no input files" in text


def test_header_names_the_matching_workflow_file() -> None:
    doc = build_workflow_document("Thin and clean", [node("a", "thin")], [], {"thin": THIN})
    assert "cwltool thin-and-clean.cwl thin-and-clean-inputs.yaml" in generate_workflow_inputs_yaml(
        "Thin and clean", doc
    )


FILTER = PortSpec(
    name="Filter",
    file_inputs={"input_rds": "File"},
    file_outputs={"output_rds": "File"},
    config_inputs={"threshold": "double", "mode": "{'type': 'enum'}", "label": "string", "seed": "int", "spec": "Spec"},
    config_types={
        "threshold": "double",
        "mode": {"type": "enum", "name": "Mode", "symbols": ["fast", "exact"]},
        "label": "string?",
        "seed": "int",
        "spec": "types.yml#Spec",
    },
    config_defaults={"threshold": 0.5, "mode": "fast"},
)


def filter_node(values: dict[str, str]) -> dict:
    return {"id": "f", "data": {"componentId": "filter", "parameterValues": values}}


def test_config_becomes_a_workflow_input_defaulting_to_the_configured_value() -> None:
    doc = build_workflow_document("Filter it", [filter_node({"threshold": "0.9"})], [], {"filter": FILTER})

    assert doc["inputs"]["step_filter__threshold"] == {"type": "double", "default": 0.9}
    assert doc["steps"]["step_filter"]["in"]["threshold"] == "step_filter__threshold"
    # unconfigured: falls back to the component's own default
    assert doc["inputs"]["step_filter__mode"] == {
        "type": {"type": "enum", "symbols": ["fast", "exact"]},
        "default": "fast",
    }
    # no value anywhere: declared without a default, optional or not
    assert doc["inputs"]["step_filter__label"] == {"type": "string?"}
    assert doc["inputs"]["step_filter__seed"] == {"type": "int"}


def test_config_with_a_type_only_the_component_resolves_stays_a_step_default() -> None:
    doc = build_workflow_document("Filter it", [filter_node({"spec": "x"})], [], {"filter": FILTER})
    assert "step_filter__spec" not in doc["inputs"]
    assert doc["steps"]["step_filter"]["in"]["spec"] == {"default": "x"}


def test_job_file_lists_the_step_configuration_with_its_values() -> None:
    doc = build_workflow_document("Filter it", [filter_node({"threshold": "0.9"})], [], {"filter": FILTER})
    text = generate_workflow_inputs_yaml("Filter it", doc)
    job = yaml.safe_load(text)

    assert job == {
        "step_filter__input_rds": {"class": "File", "path": "/path/to/input_rds"},
        "step_filter__threshold": 0.9,
        "step_filter__mode": "fast",
        "step_filter__label": None,
        "step_filter__seed": None,
    }
    assert set(job) == set(doc["inputs"])
    assert "# seed (int, required)" in text
    assert "# mode (enum: fast, exact)" in text
