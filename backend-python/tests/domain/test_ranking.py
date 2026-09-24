import uuid

from app.domain.compatibility.port_check import ConnectionStatus
from app.domain.compatibility.ranking import NO_DATA_INPUTS_SCORE, Match, OutputFrame, match_component, rank_key
from tests.domain.conftest import EDAM, GEOJSON, GEOPACKAGE, OTHER, SHAPEFILE, VECTOR, input_, output

NEWER, OLDER = uuid.uuid4(), uuid.uuid4()

STACK = [
    OutputFrame(component_id=NEWER, component_name="remove-outliers", outputs=[output("File")]),
    OutputFrame(component_id=OLDER, component_name="load-tracking-data", outputs=[output("File[]")]),
]


def test_empty_canvas_scores_everything_zero() -> None:
    assert match_component([input_()], []) == Match(score=0)


def test_candidate_without_data_inputs_sorts_below_everything() -> None:
    match = match_component([input_("string"), output("File")], STACK)
    assert match == Match(score=NO_DATA_INPUTS_SCORE)


def test_most_recent_matching_frame_wins() -> None:
    # untyped ports: the types fit, the formats are unknown - an unverified match
    match = match_component([input_()], STACK)
    assert (match.score, match.status) == (3, ConnectionStatus.UNVERIFIED)
    assert match.frame is not None and match.frame.component_name == "remove-outliers"


def test_falls_back_to_an_older_frame() -> None:
    # only File[] is accepted, which the newest frame (File) cannot satisfy
    match = match_component([input_("File[]")], STACK)
    assert match.score == 1
    assert match.frame is not None and match.frame.component_name == "load-tracking-data"


def test_nothing_matching_scores_zero() -> None:
    frames = [OutputFrame(component_id=OLDER, component_name="split", outputs=[output("File")])]
    assert match_component([input_("File[]")], frames) == Match(score=0)


def test_verified_match_outranks_unverified_in_the_same_frame(service) -> None:
    frames = [OutputFrame(component_id=OLDER, component_name="load", outputs=[output(format=GEOJSON, ontology_url=EDAM)])]
    verified = match_component([input_(format=VECTOR, ontology_url=EDAM)], frames, service)
    unverified = match_component([input_(format=VECTOR, ontology_url=OTHER)], frames, service)
    assert (verified.score, verified.status) == (2, ConnectionStatus.COMPATIBLE)
    assert (unverified.score, unverified.status) == (1, ConnectionStatus.UNVERIFIED)


def test_frame_rejected_by_the_service_is_skipped(service) -> None:
    frames = [
        OutputFrame(component_id=NEWER, component_name="newest", outputs=[output(format=GEOPACKAGE, ontology_url=EDAM)]),
        OutputFrame(component_id=OLDER, component_name="oldest", outputs=[output(format=SHAPEFILE, ontology_url=EDAM)]),
    ]
    match = match_component([input_(format=SHAPEFILE, ontology_url=EDAM)], frames, service)
    assert match.frame is not None and match.frame.component_name == "oldest"


class TestRankKey:
    @staticmethod
    def order(*candidates: tuple[str, int, bool]) -> list[str]:
        ranked = sorted(candidates, key=lambda c: rank_key(Match(score=c[1]), c[2], c[0]))
        return [name for name, _, _ in ranked]

    def test_higher_score_first(self) -> None:
        assert self.order(("low", 1, False), ("high", 3, False)) == ["high", "low"]

    def test_favourites_first_within_a_score(self) -> None:
        assert self.order(("plain", 2, False), ("starred", 2, True)) == ["starred", "plain"]

    def test_favourite_never_outranks_a_better_fit(self) -> None:
        assert self.order(("starred", 1, True), ("fits", 3, False)) == ["fits", "starred"]

    def test_name_breaks_remaining_ties(self) -> None:
        assert self.order(("beta", 0, False), ("Alpha", 0, False)) == ["Alpha", "beta"]
