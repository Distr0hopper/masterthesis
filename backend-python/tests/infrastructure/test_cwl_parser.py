import yaml

from app.domain.models.parameter import Parameter, ParameterDirection
from app.infrastructure.cwl.cwl_parser import (
    extract_parameters,
    generate_inputs_yaml,
    inject_cwl_version,
    inject_description,
    same_cwl_document,
)

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
    parameter = Parameter(name="label", cwl_type="string", default_value="Grüße", direction=ParameterDirection.INPUT)
    inputs = generate_inputs_yaml([parameter], "tool", 1)
    assert "label: Grüße" in inputs


def test_defaults_are_stored_the_way_the_builder_reads_them() -> None:
    tool = TOOL.replace(
        "inputs: {}",
        "inputs:\n"
        "  keep: {type: boolean, default: true}\n"
        "  speed: {type: double, default: 20.5}\n"
        "  ids: {type: 'string[]', default: [a, b]}\n"
        "  unit: {type: string, default: m}",
    )
    defaults = {p.name: p.default_value for p in extract_parameters(tool)}
    # JSON for anything that isn't text - `true`, never Python's `True`
    assert defaults == {"keep": "true", "speed": "20.5", "ids": '["a", "b"]', "unit": "m"}


def _input(name: str, cwl_type: str, default: str | None = None) -> Parameter:
    return Parameter(name=name, cwl_type=cwl_type, default_value=default, direction=ParameterDirection.INPUT)


def test_inputs_yaml_lists_only_inputs() -> None:
    output = Parameter(name="output_rds", cwl_type="File", direction=ParameterDirection.OUTPUT)
    job = yaml.safe_load(generate_inputs_yaml([_input("input_rds", "File"), output], "tool", 1))
    # outputs are cwltool's to write - a placeholder for them would only mislead
    assert job == {"input_rds": {"class": "File", "path": "/path/to/input"}}


def test_inputs_yaml_takes_each_default_typed() -> None:
    parameters = [
        _input("keep", "boolean", "true"),
        # stored before the parser wrote JSON - still read as the boolean it is
        _input("legacy", "boolean", "True"),
        _input("window", "int", "5"),
        _input("speed", "double", "20.5"),
        _input("ids", "string[]", '["a", "b"]'),
    ]
    job = yaml.safe_load(generate_inputs_yaml(parameters, "tool", 1))
    assert job == {"keep": True, "legacy": True, "window": 5, "speed": 20.5, "ids": ["a", "b"]}


def test_an_input_without_a_default_is_left_null_and_says_so() -> None:
    inputs = generate_inputs_yaml([_input("maxspeed", "double"), _input("strict", "boolean")], "tool", 1)
    # no made-up 0 or false that would run silently with the wrong configuration
    assert yaml.safe_load(inputs) == {"maxspeed": None, "strict": None}
    assert "maxspeed: null  # double, no default - set a value" in inputs


# --- comparing two CWL texts ------------------------------------------------------------

REFORMATTED_TOOL = """
baseCommand:
  - echo
class: CommandLineTool
cwlVersion: v1.2
inputs: {}
outputs: {}
"""


def test_reformatting_a_document_is_no_change() -> None:
    # reindented, keys reordered, flow list written as block list
    assert same_cwl_document(TOOL, REFORMATTED_TOOL)


def test_changing_what_a_document_says_is_a_change() -> None:
    assert not same_cwl_document(TOOL, TOOL.replace("echo", "cat"))


def test_text_that_isnt_yaml_is_compared_as_text() -> None:
    broken = "class: [unclosed"
    assert same_cwl_document(broken, broken)
    assert not same_cwl_document(broken, broken + " ")


def test_the_name_type_shorthand_keeps_its_type() -> None:
    from app.infrastructure.cwl.cwl_parser import extract_parameters

    cwl = """\
cwlVersion: v1.2
class: CommandLineTool
inputs:
  tracks: File
  maybe: File?
  ids: string[]
  speed: {type: double, default: 20}
  bare:
outputs:
  cleaned: File
"""
    types = {(p.name, p.direction): p.cwl_type for p in extract_parameters(cwl)}
    assert types == {
        ("tracks", ParameterDirection.INPUT): "File",
        ("maybe", ParameterDirection.INPUT): "File",
        ("ids", ParameterDirection.INPUT): "string[]",
        ("speed", ParameterDirection.INPUT): "double",
        ("bare", ParameterDirection.INPUT): "string",
        ("cleaned", ParameterDirection.OUTPUT): "File",
    }
