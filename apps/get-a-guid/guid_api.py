import os
from flask import Blueprint, Flask, abort
from flask_restplus import Resource, Api, fields, reqparse
from guidmint import PseudoMint, MD5Mint, __version__ as mint_version

api_version = "0.3.0"

guid_bp = Blueprint('guid_api', __name__)
guid_api = Api(guid_bp, title='GUIDMint REST API', doc='/doc')

mints = {
    "pseudonym": PseudoMint(),
    "md5":       MD5Mint()
}

@guid_api.route('/version')
class Version(Resource):
    def get(self):
        res = {'version':
                   {'mint': mint_version,
                    'api': api_version}}
        return res


@guid_api.route('/mints')
class Mints(Resource):
    def get(self):
        return mints.keys()


@guid_api.route('/<string:mint_id>/pseudo_id')
class PseudoID(Resource):

    pseudo_id_fields = guid_api.model('pseudo_id', {
        'guid':   fields.String,
        'name':   fields.String,
        'gender': fields.String,
        'dob':    fields.String
    })

    parser = reqparse.RequestParser()
    parser.add_argument('value',  help='Subject name or other id (req\'d)', required=True)
    parser.add_argument('gender', help='Subject gender (M, F, U) (opt)',
                                  choices=('M', 'F', 'U'), default='U')
    parser.add_argument('dob',    help='Date of birth (%Y-%m-%d) (opt)')
    parser.add_argument('age',    help='Age (int) (opt)', type=int)

    @guid_api.marshal_with(pseudo_id_fields)
    @guid_api.expect(parser)
    def get(self, mint_id):

        if mint_id not in mints.keys():
            abort(400)

        args = self.parser.parse_args()

        value = args.get('value')
        gender = args.get('gender')
        dob = args.get('dob')
        age = args.get('age')

        g, n, d = mints[mint_id].pseudo_identity(value, gender=gender, age=age, dob=dob)

        return {
            'guid': g,
            'name': n,
            'gender': gender,
            'dob': d
        }

if __name__ == '__main__':

    # This works nicely with Heroku
    port = int(os.environ.get('PORT', 5000))
    if port is 5000:
        host = None
    else:
        host = '0.0.0.0'

    # For testing only
    app = Flask(__name__)
    app.register_blueprint(guid_bp)
    app.run(debug=True)