#!/usr/bin/env python
from flask import Flask, render_template, flash, request, redirect, url_for


app = Flask(__name__)

# Define functions
def geocode_location(location):
    pass

# Define routes
@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

@app.route('/results', methods=['POST'])
def return_results():
    if request.method == 'POST':
        input_location = request.form.get('location')
        time = request.form.get('time')
        location = geocode_location(input_location)
    return render_template('results.html', location=location, time=time)

if __name__ == "__main__":
    app.run(host='0.0.0.0', debug=False)
