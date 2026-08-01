class EmailAlreadyRegisteredError(Exception):
    def __init__(self) -> None:
        super().__init__("Email already registered")
