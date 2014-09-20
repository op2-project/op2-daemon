
from flask import Flask, render_template
from op2d.resources import Resources

__all__ = ['app']


app = Flask(__name__, template_folder=Resources.get('frontend'))

@app.route('/')
def index():
    return render_template('index.html')

