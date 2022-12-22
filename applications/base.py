import json

from django.views import View
from django.http.response import HttpResponse, HttpResponseBadRequest, JsonResponse
from django.conf import settings
from applications.utils import print_db_queries


class BaseView(View):
    def get(self, req):
        args = req.GET

        try:
            if req.META.get('CONTENT_TYPE') == 'application/json':
                args = json.loads(req.body)
        except json.JSONDecodeError:
            return HttpResponseBadRequest('Invalid Json data')

        response = self.execute_get(**args)
        #
        if settings.IS_DEV:
            print_db_queries()

        return JsonResponse(response)
