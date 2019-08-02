from django.http import HttpResponse


class AllowCORSMixin(object):

    def add_access_control_headers(self, response):
        response["Access-Control-Allow-Origin"] = "http://sbs.denmasoft.com"
        response["Access-Control-Allow-Methods"] = "GET"
        response["Access-Control-Max-Age"] = "1000"
        response["Access-Control-Allow-Headers"] = "X-Requested-With, Content-Type"

    def options(self, request, *args, **kwargs):
        response = HttpResponse()
        self.add_access_control_headers(response)
        return response