import yaml

from app.domain.models.parameter import Parameter, ParameterDirection
from app.infrastructure.cwl.cwl_parser import generate_inputs_yaml, inject_cwl_version, inject_description

TOOL = "cwlVersion: v1.2\nclass: CommandLineTool\nbaseCommand: [echo]\ninputs: {}\noutputs: {}\n"
UMLAUTS = "Hier ist eine äußerst längere Description mit vielen Umlauten wie Öl, Übung und Grüße"


def test_description_keeps_umlauts_readable() -> None:
    cwl = inject_description(TOOL, UMLAUTS)
    assert UMLAUTS in cwl
    assert "\\x" not in cwl
    assert yaml.safe_load(cwl)["doc"] == UMLAUTS


def test_escaped_doc_from_older_uploads_comes_out_readable() -> None:
    # CWL stored before the fix carries the escaped form - it must download readable now
    stored = TOOL + 'doc: "Hier ist eine \\xE4u\\xDFerst l\\xE4ngere Description"\n'
    cwl = inject_description(stored, "Hier ist eine äußerst längere Description")
    assert "äußerst längere" in cwl
    assert "\\x" not in cwl


def test_cwl_version_injection_keeps_umlauts_readable() -> None:
    cwl = inject_cwl_version(TOOL.replace("cwlVersion: v1.2\n", "") + f"doc: {UMLAUTS}\n", "v1.2")
    assert UMLAUTS in cwl
    assert "\\x" not in cwl


def test_inputs_yaml_keeps_umlauts_in_string_defaults() -> None:
    parameter = Parameter(
        name="label", cwl_type="string", default_value="Grüße", direction=ParameterDirection.INPUT
    )
    inputs = generate_inputs_yaml([parameter], "tool", 1)
    assert "label: Grüße" in inputs
