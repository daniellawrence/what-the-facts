from flask import Flask, jsonify, request, render_template
from flask.json import JSONEncoder as BaseEncoder


from wtf import WTF, WTFResponse, c


app = Flask(__name__)
h = WTF(c)


class JSONEncoder(BaseEncoder):
    def default(self, o):
        if isinstance(o, WTFResponse):
            return o.data
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
        'missing_keys': set(h.hierachy_keys) - set(data_filter.keys())
    })


@app.route('/fetch/<lookup_key>/')
def fetch(lookup_key):
    data_filter = request.args
    data = h.fetch(lookup_key, **data_filter)
    return jsonify({
        'lookup_key': lookup_key,
        'value': data,
        lookup_key: data,
        'meta': data.metadata
    })

@app.route('/fetch_list/<lookup_key>/')
def fetch_list(lookup_key):
    data_filter = request.args
    data = h.fetch_list(lookup_key, **data_filter)
    return jsonify({
        'lookup_key': data,
        'meta': data.metadata
    })


@app.route('/fetch_merge/<lookup_key>/')
def fetch_merge(lookup_key):
    data_filter = request.args
    data = h.fetch_merge(lookup_key, **data_filter)
    return jsonify({
        'lookup_key': data,
        'meta': data.metadata
    })


@app.route('/dump/')
def dump():
    data_filter = request.args
    data = h.dump(**data_filter)
    return jsonify({
        'lookup_key': data,
        'meta': data.metadata
    })


if __name__ == '__main__':
    app.debug = True
    app.run()
