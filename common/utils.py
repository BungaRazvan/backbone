def get_api_key(request):

    header_keys = ["X-API-KEY", "x-api-key", "HTTP_X_API_KEY"]

    for key in header_keys:
        value = request.headers.get(key)
        if value:
            return value

        value = request.META.get(key)
        if value:
            return value

    return None
