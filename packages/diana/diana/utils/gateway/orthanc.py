# Diana-agnostic API for orthanc, no endpoint or dixel dependencies


import json, logging, re, time
from typing import Mapping
from jsmin import jsmin
import attr
from .requester import Requester
from diana.utils.dicom.dicom_level import DicomLevel


@attr.s
class Orthanc(Requester):
    user = attr.ib(default="orthanc")
    password = attr.ib(default="orthanc")
    auth = attr.ib(init=False)

    @auth.default
    def set_auth(self):
        return (self.user, self.password)

    # Wrapper for requester calls

    def get(self, resource: str, params=None):
        self.logger.debug("Getting {} from orthanc".format(resource))
        url = self._url(resource)
        return self._get(url, params=params, auth=self.auth)

    def put(self, resource: str, data=None):
        self.logger.debug("Putting {} into orthanc".format(resource))
        url = self._url(resource)
        return self._put(url, data=data, auth=self.auth)

    def post(self, resource: str, data=None, json: Mapping=None, headers: Mapping=None):
        self.logger.debug("Posting {} to orthanc".format(resource))
        url = self._url(resource)
        return self._post(url, data=data, json=json, auth=self.auth, headers=headers)

    def delete(self, resource: str):
        self.logger.debug("Deleting {} from orthanc".format(resource))
        url = self._url(resource)
        return self._delete(url, auth=self.auth)

    # item handling by oid and level

    def get_item(self, oid: str, level: DicomLevel, view: str="meta"):
        # View in [meta, tags, file*, image*, archive**]
        # * only instance level
        # * only series or study level

        params = None
        if view == "meta":
            postfix = None

        elif view == "tags":
            if level == DicomLevel.INSTANCES:
                postfix = "tags"
            else:
                postfix = "shared-tags"
            params = [("simplify", True)]

        elif view == "file" and level == DicomLevel.INSTANCES:
            postfix = "file"  # single dcm

        elif view == "image" and level == DicomLevel.INSTANCES:
            postfix = "preview"  # single dcm

        elif view == "archive" and level < DicomLevel.INSTANCES:
            postfix = "archive"   # zipped archive

        else:
            self.logger.error("Unsupported get view format {} for {}".format(view, level))
            return

        if postfix:
            resource = "{}/{}/{}".format(level, oid, postfix)
        else:
            resource = "{}/{}".format(level, oid)

        return self.get(resource, params)

    def put_item(self, file):
        resource = "instances"
        headers = {'content-type': 'application/dicom'}
        self.post(resource, data=file, headers=headers)

    def delete_item(self, oid: str, level: DicomLevel):
        resource = "{}/{}".format(level, oid)
        return self.delete(resource)

    def anonymize_item(self, oid: str, level: DicomLevel, replacement_dict: Mapping=None):

        resource = "{}/{}/anonymize".format(level, oid)

        if replacement_dict:
            # replacement_json = json.dumps(replacement_dict)
            # data = replacement_json
            headers = {'content-type': 'application/json'}
            return self.post(resource, json=replacement_dict, headers=headers)

        return self.post(resource)

    def find(self, query: Mapping, remote_aet: str, retrieve_dest: str=None):

        resource = 'modalities/{}/query'.format(remote_aet)
        headers = {"Accept-Encoding": "identity",
                   "Accept": "application/json"}

        r = self.post(resource, json=query, headers=headers)

        if not r:
            self.logger.warning("No reply from orthanc remote lookup")
            return

        qid = r["ID"]
        resource = 'queries/{}/answers'.format(qid)

        r = self.get(resource)

        if not r:
            self.logger.warning("No answers from orthanc lookup")
            return

        answers = r
        ret = []
        for aid in answers:
            resource = 'queries/{}/answers/{}/content?simplify'.format(qid, aid)
            r = self.get(resource)
            if not r:
                self.logger.warning("Bad answer from orthanc lookup")
                return
            ret.append(r)

            # If retrieve_dest defined, move data there (usually 1 study to here)
            if retrieve_dest:
                resource = 'queries/{}/answers/{}/retrieve'.format(qid, aid)
                headers = {'content-type': 'application/text'}
                rr = self.post(resource, data=retrieve_dest, headers=headers)
                # self.logger.debug(retrieve_dest)
                # self.logger.debug("Retrieved {}".format(rr))

        # Returns an array of answers
        return ret

    def send_item(self, oid: str, dest: str, dest_type):
        resource = "/{}/{}/store".format(dest_type, dest)
        data = oid
        headers = {'content-type': 'application/text'}
        self.post(resource, data=data, headers=headers)

    def statistics(self):
        return self.get("statistics")

    def reset(self):
        return self.post("tools/reset")

    def changes(self, current=0, limit=10):
        params = { 'since': current, 'limit': limit }
        return self.get("changes", params=params)

@attr.s
class OrthancReconfigurator():
    # Sometimes you just have to rewrite the Orthanc configuration after its already setup
    fp = attr.ib("/etc/orthanc/orthanc.json")
    gateway = attr.ib(type=Orthanc, default=None)

    logger = attr.ib(init=False)

    @logger.default
    def get_logger(self):
        return logging.getLogger(__name__)

    def update(self, new_conf):
        changed = False

        self.logger.debug("Attempting to update orthanc config {}".format(self.fp))

        with open(self.fp) as f:

            content = f.read()
            # logging.debug(content)

            for key, value in new_conf.items():
                pattern = r"\"{key}\" : (\{{.*?\}})".format(key=key)
                # self.logger.debug(pattern)
                match = re.search(pattern, content, re.DOTALL )

                section_str = match.group(1)
                self.logger.debug("Found {}".format(section_str))

                # Strip comments
                minified = jsmin(section_str)
                # self.logger.debug(minified)

                section =  json.loads( minified )
                # self.logger.debug(section)
                new_section = {**section, **value}

                if section != new_section:
                    changed=True

                    new_section_str = "\"{key}\" : {data}".format(
                        key=key,
                        data=json.dumps(new_section)
                    )
                    new_content = re.sub(pattern, new_section_str, content, flags=re.DOTALL)
                    self.logger.debug(new_content)

        if changed:
            self.logger.debug("Found changes, rewriting config")
            with open(self.fp, 'w') as f:
                f.write(new_content)
            if self.gateway:
                self.logger.debug("Bouncing service")
                self.gateway.reset()
                # Give it a few seconds to come back
                time.sleep(3.0)
        else:
            self.logger.debug("No changes made")

    def add_user(self, name, password):
        new_config = {
            'RegisteredUsers':
                { name: password }
        }
        self.update( new_config )

    def add_modality(self, name, aet, host, port):
        new_config = {
            'DicomModalities': {
                name: [ aet, host, int(port) ]
        }}
        self.update( new_config )


