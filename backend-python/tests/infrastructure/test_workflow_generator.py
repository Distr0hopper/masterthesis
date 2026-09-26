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
        "Thin and clean", [node("a", "thin"), node("b", "outliers")], [edge("a", "b")], {"thin": THIN, "outliers": OUTLIERS}
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
    assert "cwltool thin-and-clean.cwl thin-and-clean-inputs.yaml" in generate_workflow_inputs_yaml("Thin and clean", doc)
