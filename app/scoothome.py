#!/usr/bin/env python
from flask import Flask, render_template, flash, request, redirect, url_for

app = Flask(__name__)

# Define functions

# Define routes
@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

if __name__ == "__main__":
    app.run(host='0.0.0.0', debug=False)
