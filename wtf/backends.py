import json
import logging
import os

import ruamel.yaml


class WTFBackend(object):

    def __init__(self, path):
        self.path = path
    
    def load(self):
        raise NotImplemented("This must return a dict")


class YAMLBackend(WTFBackend):
    def load(self):
        path = os.path.join("data", self.path)

        try:
            with open(path) as f:
                return ruamel.yaml.safe_load(f)
        except Exception as error:
            logging.error(error)
        return


class JSONBackend(WTFBackend):
    def load(self):
        path = os.path.join("data", self.path)

        try:
            with open(path) as f:
                return json.load(f)
        except Exception as error:
            logging.error(error)
        return
