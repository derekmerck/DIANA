import os, logging, json
from datetime import datetime
from hashlib import md5
import markdown
import yaml
from flask import Flask, render_template, Markup, abort, session, flash, request, redirect, url_for
from flask_httpauth import HTTPBasicAuth
from werkzeug.utils import secure_filename
from jinja2 import FileSystemLoader, Environment

# gunicorn -b 0.0.0.0:5000 trialist:app

__version__ = "0.2.3"
app = Flask(__name__)

logger = logging.getLogger('Trialist')
logger.setLevel(logging.DEBUG)

md_logger = logging.getLogger("MARKDOWN")
md_logger.setLevel(logging.WARNING)

# Allowable uploads
ALLOWED_EXTENSIONS = (['dcm', 'zip'])

# Get config info
config_file = os.environ.get('DIANA_TRIALIST_CONFIG', '/etc/trialist/config.yml')
with open(config_file) as f:
    config = yaml.load(f)

auth = HTTPBasicAuth()
app.config['SALT'] = os.environ.get('DIANA_TRIALIST_SALT', "TR1@L15T!")
app.config['ENABLE_AUTH'] = json.loads(os.environ.get('DIANA_TRIALIST_ENABLE_AUTH', "true").lower())
if app.config['ENABLE_AUTH']:
    user_file = os.environ.get('DIANA_TRIALIST_USERS', '/etc/trialist/users.yml')
    with open(user_file) as f:
        users = yaml.load(f)

# Configure app
app.config['UPLOAD_FOLDER'] = config.get('upload_base_dir')
app.config['SESSION_TYPE'] = 'filesystem'
# Use a random secret key, we don't need to keep client info across runs
app.secret_key = os.urandom(24)

# --------------------------
# Setup pages
# --------------------------

def prerender(config):
    """
    Create markdown files for index and study upload pages
    """

    def render_from_template(directory, template_name, **kwargs):
        loader = FileSystemLoader(directory)
        env = Environment(loader=loader)
        template = env.get_template(template_name)
        return template.render(**kwargs)

    pages = {'index': render_from_template('templates', 'index.md.j2', **config)}

    for trial in config['trials']:

        trial['domain'] = config['domain']
        pages['upload_'+trial['study_id']] = \
            render_from_template('templates', 'upload.md.j2',
                                 trial_base_port = config['trial_base_port'],
                                 **trial)

    return pages


# Create pages
pages = prerender(config)


# --------------------------
# Simple Auth
# --------------------------

# Super simple password check
@auth.verify_password
def verify_pw(username, password):

    if not app.config['ENABLE_AUTH']:
        return True

    if username in users:

        if users[username].get('password'):
            if password == users[username].get('password'):
                session['username'] = username
                return True

        elif users[username].get('hash'):
            if md5(password+app.config['SALT']).hexdigest() == users[username].get('hash'):
                session['username'] = username
                return True

    return False


# --------------------------
# URL to page mapping
# --------------------------

# Render Markdown content to html
def render_md(content, template='strapdown.html.j2', **kwargs):
    title = config['title']
    content = Markup(markdown.markdown(content, extensions=['markdown.extensions.extra']))

    vars = locals()
    vars.update(kwargs)

    return render_template(template, **vars)


@app.route('/')
def render_index():
    return render_md(pages['index'])


@app.route('/<study_id>/upload')
@auth.login_required
def render_upload(study_id):
    if 'upload_'+study_id not in pages.keys():
        abort(404)
    else:
        return render_md(pages['upload_' + study_id])


@app.route('/<study_id>/uploader', methods=['GET', 'POST'])
@auth.login_required
def upload_file(study_id):

    def allowed_file(filename):
        return '.' in filename and \
               filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

    upload_url = url_for('render_upload', study_id=study_id)
    # logger.warning( upload_url )

    if request.method == 'POST':
        # check if the post request has the file part
        if 'file' not in request.files:
            flash('Could not upload - No file part in submission')
            return redirect(upload_url)
        file = request.files['file']
        if file.filename == '':
            flash('Could not upload - No selected file')
            return redirect(upload_url)
        if not allowed_file(file.filename):
            flash('Could not upload - Not an allowed filer extension (.zip, .dcm)')
            return redirect(upload_url)
        if file:
            try:
                os.makedirs(os.path.join( app.config['UPLOAD_FOLDER'], study_id ), exist_ok=True )
                file.save(os.path.join( app.config['UPLOAD_FOLDER'], study_id, secure_filename(file.filename)) )

                meta = {
                  'file': secure_filename(file.filename),
                  'sender': session.get('username', "Unknown"),
                  'time': datetime.now().isoformat(),
                  'source': request.base_url
                }
                meta_file = os.path.splitext( secure_filename(file.filename) )[0] + ".yml"

                with open(os.path.join( app.config['UPLOAD_FOLDER'], study_id, meta_file), 'w') as f:
                    yaml.dump(meta, f)

                flash('File uploaded')
            except PermissionError:
                flash('Could not upload - Permission denied')

            return redirect(upload_url)

    return redirect(upload_url)


