import os
from flask import Flask
from flask_cors import CORS

# Import our main API handler
from api.index import handler

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>', methods=['GET', 'POST', 'OPTIONS'])
def catch_all(path):
    """Handle all API routes"""
    from flask import request, jsonify
    
    # Convert Flask request to our handler format
    event = {
        'httpMethod': request.method,
        'path': '/' + path if path else '/',
        'body': request.get_json() if request.is_json else None,
        'headers': dict(request.headers),
        'queryStringParameters': request.args.to_dict()
    }
    
    # Call our main handler
    response = handler(event, None)
    
    # Convert response to Flask format
    return response['body'], response['statusCode'], response.get('headers', {})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False)
