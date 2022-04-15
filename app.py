import os

from flask import Flask, render_template, request, jsonify

from database import Database

app = Flask(__name__)
db = Database()


@app.route('/')
def index():
    """
    Renders the form for the user to enter the url and keyword
    """
    return render_template('index.html')


@app.route('/count', methods=['POST'])
def count():
    """
    Counts the number of times the keyword appears in the url and pages linked by it.
    """
    data = request.get_json()
    url = data.get('url')
    keyword = data.get('keyword')
    errors = []
    if not url:
        errors.append({"message": "Missing required field: url"})
    if not keyword:
        errors.append({"message": "Missing required field: keyword"})
    response = {}
    if not errors:
        db.store_url(url)
        response['result'] = {'count': db.count(url, keyword)}
    if errors:
        response['errors'] = errors
    return jsonify(response)


if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=True, host='0.0.0.0', port=port)
