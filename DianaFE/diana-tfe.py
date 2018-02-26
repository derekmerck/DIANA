import os
import sys
import logging
import dateutil.parser
import csv

from flask import Flask, render_template, Markup, abort
import markdown
from jinja2 import FileSystemLoader, Environment
import yaml
from bokeh.plotting import figure, output_file, show
from bokeh.embed import components
from splunklib import client

from flask_httpauth import HTTPBasicAuth

# In case DIANA is being run from folders
sys.path.append('../../../DIANA')
from utilities.GUIDMint import Get_a_GUID

__version__ = "0.1.0"

app = Flask(__name__)
app.register_blueprint(Get_a_GUID.api_bp, url_prefix='/guid')

auth = HTTPBasicAuth()

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger('DIANA TFE')

from hashlib import md5

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


@app.route('/')
def render_index():
    return render_md(pages['index'])

@app.route('/upload/<study_id>')
@auth.login_required
def render_upload(study_id):
    if 'upload_'+study_id not in pages.keys():
        abort(404)
    else:
        return render_md(pages['upload_' + study_id])


@app.route('/stats/<study_id>')
def render_stats(study_id):
    if 'stats_'+study_id not in pages.keys():
        abort(404)
    if not splunk:
        abort(400)
    else:

        port = 0
        for network, value in config['studies'].iteritems():
            for study, value in value.iteritems():
                logging.debug(value['study_id'])
                if value['study_id'] == study_id:
                    port = value['ports']['archive_api']
        if not port:
            abort(400)

        # Run a one-shot search and display the results using the results reader

        # Set the parameters for the search:
        kwargs_oneshot = {"earliest_time": "1995-01-01T12:00:00.000",
                          "latest_time": "now",
                          "count": 0,
                          "output_mode": "csv"}
        searchquery_oneshot = "search index=dicom host=*{port} | dedup AccessionNumber | bin _time span=1months | chart count by _time".format(port=port)
        oneshotsearch_results = splunk.jobs.oneshot(searchquery_oneshot, **kwargs_oneshot)
        reader = csv.reader(oneshotsearch_results)

        dates = []
        counts = []
        next(reader, None)
        next(reader, None)
        for row in reader:
            print row
            dates.append(dateutil.parser.parse(row[0]))
            counts.append(row[1])

        # create a new plot with a datetime axis type
        p = figure(plot_width=800, plot_height=250, x_axis_type="datetime")
        # Comes in 1 month chunks convert 0.9 mo to ms for width
        p.vbar(x=dates, bottom=0, top=counts, color='blue', width=0.9 * 30 * 24 * 60 * 60 * 1000)
        # Get pieces to embed on web page
        bokeh_script, bokeh_div = components(p)

        return render_md(pages['stats_' + study_id], bokeh_div=bokeh_div, bokeh_script=bokeh_script)


def prerender(config_file):

    def render_from_template(directory, template_name, **kwargs):
        loader = FileSystemLoader(directory)
        env = Environment(loader=loader)
        template = env.get_template(template_name)
        return template.render(**kwargs)

    with open(config_file) as f:
        config = yaml.load(f)

    pages = {'index': render_from_template('templates', 'index.md.j2', **config)}

    for network, value in config['studies'].iteritems():
        for study, value in value.iteritems():
            value['domain'] = config['domain']
            logger.debug(value)
            pages['upload_'+value['study_id']] = render_from_template('templates', 'upload.md.j2', **value)
            pages['stats_'+value['study_id']] = render_from_template('templates', 'stats.md.j2', **value)

    return config, pages

config_file = os.environ['tfe_config']
config, pages = prerender(config_file)

splunk_host = os.environ['splunk_host']
splunk_password = os.environ['splunk_password']

# Create a splunk service instance and log in
splunk = client.connect(host=splunk_host,
                        port=8089,
                        username="admin",
                        password=splunk_password)

if __name__ == '__main__':
    logger.debug('Starting up TFE app')
    app.run(host="0.0.0.0")




