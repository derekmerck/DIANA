import os
import markdown
from flask import Flask, Markup, render_template
from guid_api import guid_bp as api, mint_version, api_version

app = Flask(__name__)
app.register_blueprint(api, url_prefix='/guid')

def read(*paths):
    """Build a file path from *paths* and return the contents."""
    with open(os.path.join(*paths), 'r') as f:
        return f.read()

@app.route('/')
def info():
    content = read(os.path.dirname(__file__), 'README.md')
    content = content + "\n\n" + "Mint version: {0} | API version: {1}".format(mint_version, api_version)
    content = Markup(markdown.markdown(content, ['markdown.extensions.extra']))
    return render_template('index.html', **locals())

if __name__ == '__main__':

    # This works nicely with Heroku
    port = int(os.environ.get('PORT', 5000))
    if port is 5000:
        host = None
    else:
        host = '0.0.0.0'

    app.run(debug=True)