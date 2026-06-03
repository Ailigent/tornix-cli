from __future__ import annotations


class EXIT:
    OK = 0
    GENERIC = 1
    USAGE = 2
    AUTH = 3
    NOT_FOUND = 4
    VALIDATION = 5
    RATE_LIMIT = 6


class TornixError(Exception):
    def __init__(self, message: str, *, status: int | None = None,
                 code: str | None = None, hint: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.status = status
        self.code = code
        self.hint = hint

    @property
    def exit_code(self) -> int:
        s = self.status
        if s == 401:
            return EXIT.AUTH
        if s == 403:
            return EXIT.AUTH
        if s == 404:
            return EXIT.NOT_FOUND
        if s in (400, 422):
            return EXIT.VALIDATION
        if s == 429:
            return EXIT.RATE_LIMIT
        return EXIT.GENERIC

    def to_dict(self) -> dict:
        return {"error": {"code": self.code, "message": self.message,
                          "status": self.status, "hint": self.hint}}
