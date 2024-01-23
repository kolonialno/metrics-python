from django.http import HttpRequest


def get_request_method(request: HttpRequest) -> str:
    if request.method not in (
        "GET",
        "HEAD",
        "POST",
        "PUT",
        "DELETE",
        "TRACE",
        "OPTIONS",
        "CONNECT",
        "PATCH",
    ):
        return "<invalid method>"

    return str(request.method)


def get_view_name(request: HttpRequest) -> str:
    view_name = "<unnamed view>"
    if hasattr(request, "resolver_match"):
        if request.resolver_match is not None:
            if request.resolver_match.view_name is not None:
                view_name = request.resolver_match.view_name

    return view_name
