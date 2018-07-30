from .mint import GUIDMint
from hashlib import md5

class MD5Mint(GUIDMint):
    """
    Simple mint that assigns ID as md5 hash
    """

    def __init__(self, prefix: str="", **kwargs):
        self.prefix = prefix
        super(MD5Mint, self).__init__(**kwargs)

    def guid(self, value: str, *args, **kwargs):
        # Accept any value and return md5 of it
        return md5(value.encode('utf-8')).hexdigest()[:self.hash_prefix_length]
