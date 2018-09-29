
from diana.apis import Splunk, Dixel
from diana.utils.dicom import DicomLevel


if __name__ == "__main__":
    test_host = "stretch64"
    remotes_tok = "abc"

    index_kwargs = {
        'host': '{}'.format(test_host),
        'hec_port': 8088,
        'hec_protocol': 'https',
        'default_index': 'remotes',
        'default_token': 'remotes_tok',
        'hec_tokens': {'remotes_tok': '{}'.format(remotes_tok)}}

    splunk = Splunk(**index_kwargs)

    splunk.put(
        Dixel(meta={'oid': "hello"}, level=DicomLevel.STUDIES),
        "test_host",
        "remotes_tok"
    )

