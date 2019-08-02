class SbsCorsMiddleware(object):
    def process_response(self, request, response):
        response["Access-Control-Allow-Origin"] = "http://sbs.denmasoft.com"
        response["Access-Control-Allow-Methods"] = "GET,POST"
        response["Access-Control-Max-Age"] = "1000"
        response["Access-Control-Allow-Headers"] = "Origin,Content-Type,Accept,Authorization"
        return response
