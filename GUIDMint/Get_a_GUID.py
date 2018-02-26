import os
from flask import Flask, render_template, Markup, Blueprint
# from flask.views import View
from flask_restplus import Resource, Api, reqparse, fields, abort
import markdown
import logging
import random
from datetime import datetime, timedelta
from GUIDMint import PseudoMint, MD5Mint, __version__

api_version = "0.2.0"

def read(*paths):
    """Build a file path from *paths* and return the contents."""
    with open(os.path.join(*paths), 'r') as f:
        return f.read()

app = Flask(__name__)
api_bp = Blueprint('guid_api', __name__,
                     template_folder='templates')
guid_api = Api(api_bp, version=__version__, title='GUIDMint API',
          description='GUIDMint API', doc='/doc')

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("Get-a-GUID")


# @guid_api.route('/ndar')
# def get_ndar_guid():
#     # TODO: Add NDAR translator
#     return "NDAR GUID translator is not implemented yet"
#
# @guid_api.route('/link')
# def link_hashes():
#     # TODO: Add DB for hash linking
#     return "Hash linking is not implemented yet"

@app.route('/info')
def info():
    content = read('README.md')
    content = content + "\n\n" + "Mint version: {0} | API version: {1}".format(__version__, api_version)
    content = Markup(markdown.markdown(content, ['markdown.extensions.extra']))
    return render_template('index.html', **locals())


@guid_api.route('/version')
class Version(Resource):
    def get(self):
        res = {'version':
                   {'mint': __version__,
                    'api': api_version}}

        return res

@guid_api.route('/mints')
class Mints(Resource):

    def get(self):
        return mints.keys()


@guid_api.route('/<string:mint_id>/pseudo_id')
class PseudoID(Resource):

    pseudo_id_fields = guid_api.model('pseudo_id', {
        'guid': fields.String,
        'name': fields.String,
        'gender': fields.String,
        'dob': fields.String
    })

    parser = reqparse.RequestParser()
    parser.add_argument('name', help='Subject name or other id (req\'d)', required=True)
    parser.add_argument('gender', help='Subject gender (M, F, U) (opt)', choices=('M', 'F', 'U'), default='U')
    parser.add_argument('dob', help='Date of birth (%Y-%m-%d) (opt)')
    parser.add_argument('age', help='Age (int) (opt)', type=int)

    @guid_api.marshal_with(pseudo_id_fields)
    @guid_api.expect(parser)
    def get(self, mint_id):

        if mint_id not in mints.keys():
            abort(400)

        args = self.parser.parse_args()

        name = args.get('name')
        gender = args.get('gender')
        dob = args.get('dob')
        age = args.get('age')

        g, n, d = mints[mint_id].pseudo_identity(name, gender=gender, age=age, dob=dob)

        return {
            'guid': g,
            'name': n,
            'gender': gender,
            'dob': d
        }

mints = {
    "pseudonym": PseudoMint(),
    "md5":    MD5Mint()
}

if __name__ == '__main__':

    # This works nicely with Heroku
    port = int(os.environ.get('PORT', 5000))
    if port is 5000:
        host = None
    else:
        host = '0.0.0.0'

    app.register_blueprint(api_bp)
    app.run(host=host, port=port)

