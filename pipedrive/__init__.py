from httplib2 import Http
from logging import getLogger

try:
    from urllib import urlencode
except ImportError:
    from urllib.parse import urlencode

import json

PIPEDRIVE_API_URL = "https://api.pipedrive.com/v1/"
logger = getLogger('pipedrive')


class PipedriveError(Exception):
    def __init__(self, response):
        self.response = response

    def __str__(self):
        return self.response.get('error', 'No error provided')


class IncorrectLoginError(PipedriveError):
    pass


class Pipedrive(object):
    def _request(self, endpoint, data, method='POST'):
        # avoid storing the string 'None' when a value is None
        data = {k: "" if v is None else v for k, v in data.items()}
        if method == "GET":
            uri = PIPEDRIVE_API_URL + endpoint + '?api_token=' + str(self.api_token)
            if data:
                uri += '&' + urlencode(data)
            response, data = self.http.request(uri, method=method, headers={'Content-Type': 'application/x-www-form-urlencoded'})
        else:
            uri = PIPEDRIVE_API_URL + endpoint + '?api_token=' + str(self.api_token)
            response, data = self.http.request(uri, method=method, body=json.dumps(data), headers={'Content-Type': 'application/json'})

        logger.debug('sending {method} request to {uri}'.format(
            method=method,
            uri=uri
        ))
        # print(json.dumps(json.loads(data.decode('utf-8')), sort_keys=True, indent=4))

        # if python2, use:
        # return json.loads(data)
        return json.loads(data.decode('utf-8'))

    def __init__(self, email, password=None):
        self.http = Http()
        if password:
            response = self._request("/authorizations/", {"email": email, "password": password})

            if 'error' in response:
                raise IncorrectLoginError(response)

            # self.api_token = response['authorization'][0]['api_token']
            self.api_token = response['data'][0]['api_token']
            print('api_token is ' + self.api_token)
        else:
            # Assume that login is actually the api token
            self.api_token = email

    def __getattr__(self, name):
        def wrapper(data={}, method='GET'):

            response = self._request(name.replace('_', '/'), data, method)

            def _generator():
                if 'error' in response:
                    raise PipedriveError(response)

                additional_data = response.get('additional_data', {})
                pagination_info = additional_data.get('pagination', {})

                logger.debug('pagination_info: {}'.format(pagination_info))
                if isinstance(response['data'], dict):
                    yield response['data']
                else:
                    yield from response['data']

                if pagination_info.get('more_items_in_collection', False):

                    data.update({
                        'start': pagination_info['next_start']
                    })

                    yield from wrapper(data, method)

            return _generator()

        return wrapper
