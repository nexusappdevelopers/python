from rest_framework.response import Response
from rest_framework import status


def _capitalize_first(value):
    """Capitalize only the first character of a string; leave others intact.
    Safely ignore non-string values (dicts/lists/None)."""
    if isinstance(value, str) and value:
        return value[0].upper() + value[1:]
    return value


def create_response(data=None, message=None, status_code=status.HTTP_200_OK, error=None):
    response_data = {}

    if error:
        response_data["message"] = _capitalize_first(error)
        response_data["status"] = status_code
    else:
        if data is not None:
            response_data["data"] = data
        response_data["message"] = _capitalize_first(message)
        response_data["status"] = status_code

    return Response(response_data, status=status_code)

