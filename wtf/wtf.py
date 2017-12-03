import collections
import logging
import re
import os

from backends import *


re_key = re.compile('{(\w+)}')


class WTFResponse(object):

    def __init__(self, data, metadata):
        self.data = data
        self.__type__ = type(data)
        self.metadata = metadata

    def __str__(self):
        return str(self.data)

    def __int__(self):
        return int(self.data)

    def __dict__(self):
        return dict(self.data)
    

class WTF(object):
    
    def __init__(self, config):
        self.config = config
        self.hierachy = set()
        self.hierachy_keys = set()
        self.parse_config()

    def parse_config(self):
        self.hierachy = self.config.get('hierachy', [])
        self.parse_hierachy_keys()

    def parse_hierachy_keys(self):
        keys = set()
        for line in self.hierachy:
            found_keys = set(re_key.findall(line))
            keys = keys.union(found_keys)
        self.hierachy_keys = keys

    def dump(self, **filter_data):
        instance_hierachy = list(reversed(list(self.filtered_hierachy(filter_data))))
        merged_data = {}
        sources = []
        
        for source in instance_hierachy:
            response = self.backend_proxy(source)
            if response:
                sources.append((True, source))
                merged_data.update(response)
            else:
                sources.append((False, source))

        return WTFResponse(merged_data, {
            'instastance_hierachy': instance_hierachy,
            'sources': sources,

        })

    def fetch(self, lookup, **filter_data):
        instance_hierachy = list(self.filtered_hierachy(filter_data))
        sources = []
        data = None
        
        for source in instance_hierachy:
            response = self.backend_proxy(source)
            if not response:
                sources.append((False, source))
                continue
                
            if lookup in response:
                sources.append((True, source))
                data = response.get(lookup)
                break
            
            sources.append((False, source))

        return WTFResponse(
            data,
            {
                'instastance_hierachy': instance_hierachy,
                'sources': sources,
                'filter': filter_data
            }
        )


    def fetch_list(self, lookup, **filter_data):
        instance_hierachy = list(self.filtered_hierachy(filter_data))
        sources = []
        merged_data = []
        
        for source in instance_hierachy:
            response = self.backend_proxy(source)
            if not response:
                sources.append((False, source))
                continue
                
            if lookup in response:
                sources.append((True, source))
                merged_data.append(response.get(lookup))
            else:
                sources.append((False, source))

        return WTFResponse(
            merged_data,
            {
                'instastance_hierachy': instance_hierachy,
                'sources': sources,
            }
        )


    def fetch_merge(self, lookup, **filter_data):
        instance_hierachy = list(reversed(list(self.filtered_hierachy(filter_data))))
        sources = []
        merged_data = {}
        
        for source in instance_hierachy:
            response = self.backend_proxy(source)
            if not response:
                sources.append((False, source))
                continue
                
            if lookup in response:
                response = response.get(lookup)
                if isinstance(response, dict):
                    sources.append((True, source))
                    merged_data.update(response)
                else:
                    raise ValueError('{}/{} must be a dict'.format(source, lookup))
            else:
                sources.append((False, source))

        return WTFResponse(
            merged_data,
            {
                'instastance_hierachy': instance_hierachy,
                'sources': sources,
            }
        )


    def backend_proxy(self, source):
        backend_type = source.split('://')[0]
        path = "://".join(source.split('://')[1:])

        try:
            if backend_type == 'yaml':
                return YAMLBackend(path).load()

            elif backend_type == 'json':
                return JSONBackend(path).load()

            elif backend_type == 'vault':
                return VaultBackend(path).load()

        except Exception as error:
            logging.error("{} failed, {}".format(source, error))
            return None

        raise Exception('unknown backend {}, for source {}, {}'.format(
            backend_type, backend_type, path))

        
    def filtered_hierachy(self, filter_data):
        self.validate_lookup_keys(filter_data.keys())
        for source in self.hierachy:
            try:
                yield source.format(**filter_data)
            except KeyError as missing_filter_data:
                continue

    def validate_lookup_keys(self, keys):
        keys = set(keys)
        invalid_keys = keys.difference(self.hierachy_keys)
        if invalid_keys:
            raise Exception("extra filter_data used, {}, ony use: {}".format(invalid_keys, self.hierachy_keys))


c = {
    'hierachy': [
        'json://hostname/{hostname}.json',
        'yaml://hostname/{hostname}.yaml',
        'yaml://app_name/{app_name}/environment/{environment}.yaml',
        'yaml://app_name/{app_name}/site/{site}.yaml',
        'yaml://app_name/{app_name}.yaml',
        'yaml://{environment}.yaml',
        'yaml://{site}.yaml',
        'yaml://{os_family}.yaml',
        'yaml://base.yaml'
    ]
}


if __name__ == '__main__':
    h = WTF(c)
    print(h.fetch('http_proxy', hostname='h1'))
    print(h.fetch_merge('app_config', hostname='h1'))
    print(h.fetch('app_config', hostname='h1'))
    print(h.dump(hostname='h1'))
