"""Use-case errors. The API layer maps them to 404, 403, 409 and 422."""


class NotFound(Exception):
    pass


class Forbidden(Exception):
    pass


class Conflict(Exception):
    pass


class Invalid(Exception):
    pass
