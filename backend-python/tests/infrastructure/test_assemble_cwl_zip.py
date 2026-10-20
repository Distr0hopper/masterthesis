"""The downloaded archive must unpack into the layout its relative paths expect."""

import io
import posixpath
import zipfile

from app.infrastructure.cwl.workflow_generator import assemble_cwl_zip


def entries(zip_bytes: bytes) -> list[str]:
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as archive:
        return sorted(archive.namelist())


def test_without_climbing_paths_everything_stays_at_the_root() -> None:
    _, content = assemble_cwl_zip("My WF", "class: Workflow", [("a.cwl", "a")], [("types/t.yml", "t")])
    assert entries(content) == ["a.cwl", "my-wf.cwl", "types/t.yml"]


def test_an_import_out_of_the_documents_folder_puts_the_documents_one_folder_down() -> None:
    # uploaded as workflow/pipeline.cwl + types/t.yml, importing ../types/t.yml
    _, content = assemble_cwl_zip(
        "My WF", "class: Workflow", [("a.cwl", "a")], [("../types/t.yml", "t"), ("../../shared/s.yml", "s")]
    )

    names = entries(content)
    assert not any(name.startswith("..") or name.startswith("/") for name in names)
    assert names == ["shared/s.yml", "workflow/types/t.yml", "workflow/workflow/a.cwl", "workflow/workflow/my-wf.cwl"]
    # each stored path, resolved from the main document, is an entry of the archive
    main_folder = posixpath.dirname("workflow/workflow/my-wf.cwl")
    for stored in ("../types/t.yml", "../../shared/s.yml", "a.cwl"):
        assert posixpath.normpath(posixpath.join(main_folder, stored)) in names
