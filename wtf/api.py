from flask import Flask, jsonify, request, render_template
from flask.json import JSONEncoder as BaseEncoder


from wtf import WTF, WTFResponse, c


app = Flask(__name__)
h = WTF(c)


class JSONEncoder(BaseEncoder):
    def default(self, o):
        if isinstance(o, WTFResponse):
            d = o.data
            d['_meta'] = o.metadata
            return d
        
        if isinstance(o, set):
            return list(o)

        return BaseEncoder.default(self, o)

app.json_encoder = JSONEncoder


@app.before_request
def purge_empty_keys():
    args = {}
    for key, value in request.args.to_dict().items():
        if value.strip() != '':
            args[key] = value
    request.args = args

    
@app.route('/')
def index():
    return render_template('index.html')


@app.route('/raw/<path:path>/')
def raw(path):
    return jsonify(h.backend_proxy(path))


@app.route('/debug/')
def keys():
    data_filter = request.args
    
    return jsonify({
        'hierachy': list(h.hierachy),
        'keys': list(h.hierachy_keys),
        'applied_hierachy': list(h.filtered_hierachy(data_filter)),
        'filter_keys': set(data_filter.keys()),
        'missing_keys': set(h.hierachy_keys) - set(data_filter.keys()),
        '_meta': {
            'applied_hierachy': list(h.filtered_hierachy(data_filter)),
        }
    })


@app.route('/fetch/<lookup_key>/')
def fetch(lookup_key):
    lookup_keys = lookup_key.split(',')
    
    data_filter = request.args
    response = h.fetch(lookup_keys, **data_filter)
    return jsonify(response)


@app.route('/fetch_list/<lookup_key>/')
def fetch_list(lookup_key):
    lookup_key = lookup_key.split(',')

    data_filter = request.args
    response = h.fetch_list(lookup_key, **data_filter)
    return jsonify(response)


@app.route('/fetch_merge/<lookup_key>/')
def fetch_merge(lookup_key):
    data_filter = request.args
    response = h.fetch_merge(lookup_key, **data_filter)
    return jsonify(response)


@app.route('/dump/')
def dump():
    data_filter = request.args
    response = h.dump(**data_filter)
    return jsonify(response)


if __name__ == '__main__':
    app.debug = True
    app.run()
