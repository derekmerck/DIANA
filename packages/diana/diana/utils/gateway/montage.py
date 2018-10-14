
import json, logging, re, time
from typing import Mapping
from jsmin import jsmin
import attr
from .requester import Requester
from diana.utils.dicom.dicom_level import DicomLevel


@attr.s
class Montage(Requester):
    user = attr.ib(default="montage")
    password = attr.ib(default="passw0rd!")
    path = attr.ib( default="api/v1")
    auth = attr.ib(init=False)

    @auth.default
    def set_auth(self):
        return (self.user, self.password)

    # Wrapper for requester calls

    def get(self, resource: str, params: Mapping=None):
        self.logger.debug("Getting {} from montage".format(resource))
        url = self._url(resource)
        return self._get(url, params=params, auth=self.auth)

    def put(self, resource: str, data=None):
        self.logger.debug("Putting {} into montage".format(resource))
        url = self._url(resource)
        return self._put(url, data=data, auth=self.auth)

    def post(self, resource: str, data=None, json: Mapping=None, headers: Mapping=None):
        self.logger.debug("Posting {} to montage".format(resource))
        url = self._url(resource)
        return self._post(url, data=data, json=json, auth=self.auth, headers=headers)

    def delete(self, resource: str):
        self.logger.debug("Deleting {} from montage".format(resource))
        url = self._url(resource)
        return self._delete(url, auth=self.auth)

    def find(self, query: Mapping, index: str="rad"):
        self.logger.debug("Searching montage")
        resource = "index/{}/search".format(index)
        return self.get(resource, params={**query, 'format': 'json'})