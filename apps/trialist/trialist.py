import os, logging
from hashlib import md5
import markdown
import yaml
from flask import Flask, render_template, Markup, abort, Blueprint, flash, request, redirect
from flask_httpauth import HTTPBasicAuth
from werkzeug.utils import secure_filename
from jinja2 import FileSystemLoader, Environment
# from bokeh.plotting import figure, output_file, show
# from bokeh.embed import components
# from splunklib import client

# In case DIANA is being run from folders
# sys.path.append('../')
# from ../get-a-guid import guid_api

__version__ = "0.2.1"

app = Flask(__name__)
# app.register_blueprint(guid_bp, url_prefix="/guid")
app.config['SESSION_TYPE'] = 'filesystem'
# Use a random secret key, we don't need to keep client info across runs
app.secret_key = os.urandom(24)
auth = HTTPBasicAuth()

logger = logging.getLogger('Trialist')

# Super simple password check
@auth.verify_password
def verify_pw(username, password):
    hash = md5(password + '+' + config['credentials']['salt']).hexdigest()
    if hash in config['credentials']['auth']:
        return True
    return False


def read(*paths):
    """Build a file path from *paths* and return the contents."""
    with open(os.path.join(*paths), 'r') as f:
        return f.read()


def render_md(content, template='strapdown.html.j2', **kwargs):
    title = config['title']
    content = Markup(markdown.markdown(content, ['markdown.extensions.extra']))

    vars = locals()
    vars.update(kwargs)

    return render_template(template, **vars)


ALLOWED_EXTENSIONS = (['dcm', 'zip'])
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/')
def render_index():
    return render_md(pages['index'])


@app.route('/<study_id>/upload')
# @auth.login_required
def render_upload(study_id):
    if 'upload_'+study_id not in pages.keys():
        abort(404)
    else:
        return render_md(pages['upload_' + study_id])


@app.route('/<study_id>/uploader', methods=['GET', 'POST'])
def upload_file(study_id):

    # logger.warning("Upload folder: {}".format(app.config['UPLOAD_FOLDER']))

    if request.method == 'POST':
        # check if the post request has the file part
        if 'file' not in request.files:
            flash('No file part submitted')
            return redirect('/{}/upload'.format(study_id))
        file = request.files['file']
        if file.filename == '':
            flash('No selected file')
            return redirect('/{}/upload'.format(study_id))
        if not allowed_file(file.filename):
            flash('Not an allowed filer extension (.zip, .dcm)')
            return redirect('/{}/upload'.format(study_id))
        if file:
            os.makedirs(os.path.join( app.config['UPLOAD_FOLDER'], study_id ), exist_ok=True )
            file.save(os.path.join( app.config['UPLOAD_FOLDER'], study_id, secure_filename(file.filename)) )
            flash('File uploaded')
            redirect('/{}/upload'.format(study_id))

    return redirect('/{}/upload'.format(study_id))

# @app.route('/<study_id>/stats')
# def render_stats(study_id):
#     if 'stats_'+study_id not in pages.keys():
#         abort(404)
#     if not splunk:
#         abort(400)
#     else:
#
#         port = 0
#         for network, value in config['studies'].iteritems():
#             for study, value in value.iteritems():
#                 logging.debug(value['study_id'])
#                 if value['study_id'] == study_id:
#                     port = value['ports']['archive_api']
#         if not port:
#             abort(400)
#
#         # Run a one-shot search and display the results using the results reader
#
#         # Set the parameters for the search:
#         kwargs_oneshot = {"earliest_time": "1995-01-01T12:00:00.000",
#                           "latest_time": "now",
#                           "count": 0,
#                           "output_mode": "csv"}
#         searchquery_oneshot = "search index=dicom host=*{port} | dedup AccessionNumber | bin _time span=1months | chart count by _time".format(port=port)
#         oneshotsearch_results = splunk.jobs.oneshot(searchquery_oneshot, **kwargs_oneshot)
#         reader = csv.reader(oneshotsearch_results)
#
#         dates = []
#         counts = []
#         next(reader, None)
#         next(reader, None)
#         for row in reader:
#             print(row)
#             dates.append(dateutil.parser.parse(row[0]))
#             counts.append(row[1])
#
#         # create a new plot with a datetime axis type
#         p = figure(plot_width=800, plot_height=250, x_axis_type="datetime")
#         # Comes in 1 month chunks convert 0.9 mo to ms for width
#         p.vbar(x=dates, bottom=0, top=counts, color='blue', width=0.9 * 30 * 24 * 60 * 60 * 1000)
#         # Get pieces to embed on web page
#         bokeh_script, bokeh_div = components(p)
#
#         return render_md(pages['stats_' + study_id], bokeh_div=bokeh_div, bokeh_script=bokeh_script)

def prerender(config_file):
    """
    Create markdown files for index and study upload pages
    """
    # global splunk
    # config['splunk_available'] = (splunk != None)

    def render_from_template(directory, template_name, **kwargs):
        loader = FileSystemLoader(directory)
        env = Environment(loader=loader)
        template = env.get_template(template_name)
        return template.render(**kwargs)

    with open(config_file) as f:

        config = yaml.load(f)


    pages = {'index': render_from_template('templates', 'index.md.j2', **config)}

    for trial in config['trials']:

        trial['domain'] = config['domain']
        pages['upload_'+trial['study_id']] = \
            render_from_template('templates', 'upload.md.j2',
                                 trial_base_port = config['trial_base_port'],
                                 **trial)
        # pages['stats_'+trial['study_id']] = render_from_template('templates', 'stats.md.j2', **trial)

    return config, pages

# if os.environ.get('splunk_host'):
#
#     try:
#
#         splunk_host = os.environ['splunk_host']
#         splunk_password = os.environ['splunk_password']
#
#         # Create a splunk service instance and log in
#         splunk = client.connect(host=splunk_host,
#                                 port=8089,
#                                 username="admin",
#                                 password=splunk_password)
#
#     except client.AuthenticationError:
#         splunk = None
#
# else:

# splunk = None

config_file = os.environ['DIANA_TRIALIST_CONFIG']
config, pages = prerender(config_file)

app.config['UPLOAD_FOLDER'] = config.get('upload_base_dir')

md_logger = logging.getLogger("MARKDOWN")
md_logger.setLevel(logging.WARNING)

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    logger.debug('Starting up DIANA Trialist server app')
    app.run(host="0.0.0.0")




