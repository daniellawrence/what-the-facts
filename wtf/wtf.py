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
        applied_hierachy = list(self.filtered_hierachy(filter_data))
        merged_data = {}
        sources = set()
        
        for source in reversed(applied_hierachy):
            response = self.backend_proxy(source)
            if response:
                sources.add(source)
                merged_data.update(response)

        return WTFResponse(merged_data, {
            'applied_hierachy': applied_hierachy,
            'sources': list(sources),

        })

    def fetch(self, lookup_list, **filter_data):

        if not isinstance(lookup_list, list):
            lookup_list = [lookup_list]
            
        applied_hierachy = list(self.filtered_hierachy(filter_data))
        sources = set()
        data = {}

        for key in lookup_list:
            key_data, key_sources = self.find_first(key, applied_hierachy)
            data.update(key_data)
            sources.update(key_sources)

        return WTFResponse(
            data,
            {
                'applied_hierachy': applied_hierachy,
                'sources': list(sources),
                'filter': filter_data
            }
        )
        

    def find_first(self, lookup_key, applied_hierachy):
        sources = set()
        data = {lookup_key: None}
        
        for source in applied_hierachy:
            response = self.backend_proxy(source)
            if not response:
                continue
                
            if lookup_key in response:
                sources.add(source)
                data = {lookup_key: response.get(lookup_key)}
                break

        return data, sources

    def find_list(self, lookup_key, applied_hierachy):
        sources = set()
        data = {lookup_key: []}

        for source in applied_hierachy:
            response = self.backend_proxy(source)
            if not response:
                continue
                
            if lookup_key in response:
                sources.add(source)
                value = response.get(lookup_key, [])
                if not isinstance(value, list):
                    # raise ValueError("{} from {} is not a list".format(lookup_key, source))
                    value = [value]
                data[lookup_key] += value

        return data, sources

    def find_dict(self, lookup_key, applied_hierachy):
        sources = set()
        data = {lookup_key: {}}

        for source in applied_hierachy:
            response = self.backend_proxy(source)
            if not response:
                continue
                
            if lookup_key in response:
                sources.add(source)
                value = response.get(lookup_key, {})
                if not isinstance(value, dict):
                    raise ValueError("{} from {} is not a Dict".format(lookup_key, source))
                data[lookup_key].update(value)

        return data, sources


    def fetch_list(self, lookup_list, **filter_data):        
        if not isinstance(lookup_list, list):
            lookup_list = [lookup_list]
            
        applied_hierachy = list(self.filtered_hierachy(filter_data))
        sources = set()
        data = {}
        errors = []

        for key in lookup_list:
            try:
                key_data, key_sources = self.find_list(key, applied_hierachy)
            except ValueError as error:
                errors.append(str(error))
                continue
            
            data.update(key_data)
            sources.update(key_sources)

        return WTFResponse(
            data,
            {
                'applied_hierachy': applied_hierachy,
                'sources': list(sources),
                'filter': filter_data,
                'errors': errors
            }
        )

    def fetch_merge(self, lookup_list, **filter_data):
        applied_hierachy = list(self.filtered_hierachy(filter_data))
        sources = set()
        data = {}
        errors = []

        for key in lookup_list:
            try:
                key_data, key_sources = self.find_list(key, applied_hierachy)
            except ValueError as error:
                errors.append(str(error))
                continue
            
            data.update(key_data)
            sources.update(key_sources)

        return WTFResponse(
            data,
            {
                'applied_hierachy': applied_hierachy,
                'sources': list(sources),
                'filter': filter_data,
                'errors': errors,
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
        'yaml://hostname/{hostname}.yaml',
        'yaml://app/{app_name}/env/{environment}.yaml',
        'yaml://app/{app_name}/site/{site}.yaml',
        'yaml://app/{app_name}.yaml',
        'yaml://env/{environment}.yaml',
        'yaml://site/{site}.yaml',
        'yaml://os/{os_family}.yaml',
        'yaml://base.yaml'
    ]
}


if __name__ == '__main__':
    h = WTF(c)
    print(h.fetch('http_proxy', hostname='h1'))
    print(h.fetch_merge('app_config', hostname='h1'))
    print(h.fetch('app_config', hostname='h1'))
    print(h.dump(hostname='h1'))
