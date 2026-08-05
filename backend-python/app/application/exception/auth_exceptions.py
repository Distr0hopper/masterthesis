class InvalidTokenError(Exception):
    def __init__(self) -> None:
        super().__init__("Invalid or expired token")