class InvalidOtpCodeError(Exception):
    def __init__(self) -> None:
        super().__init__("Invalid or expired code")


class OtpCodeExpiredError(Exception):
    def __init__(self) -> None:
        super().__init__("Code has expired")


class OtpAttemptsExceededError(Exception):
    def __init__(self) -> None:
        super().__init__("Too many incorrect attempts, request a new code")