class InvalidCwlError(Exception):
    def __init__(self, context: str, reason: str) -> None:
        super().__init__(f"{context} CWL could not be parsed: {reason}")


class NotComponentCreatorError(Exception):
    def __init__(self) -> None:
        super().__init__("Only the creator of this component may perform this action")