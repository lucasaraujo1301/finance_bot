class CreateRemoteUserError(Exception):
    def __init__(self, message: str = "Could not create user in remote API.") -> None:
        super().__init__(message)
