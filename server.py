import os
from flask import Flask, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

@app.route('/health')
def health_check():
    """Health check endpoint for Render"""
    return jsonify({"status": "healthy", "message": "Server is running"})

# Simple route to avoid 404 errors
@app.route('/')
def home():
    return jsonify({"status": "running", "message": "Humanizer Backend API - Ready"})

# Catch-all route for API endpoints
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>', methods=['GET', 'POST', 'OPTIONS'])
def catch_all(path):
    """Handle all API routes"""
    from flask import request
    
    # Convert Flask request to our handler format
    event = {
        'httpMethod': request.method,
        'path': '/' + path if path else '/',
        'body': request.get_json() if request.is_json else None,
        'headers': dict(request.headers),
        'queryStringParameters': request.args.to_dict()
    }
    
    try:
        # Import handler - but be aware this may take time due to model loading
        from api.index import handler
        response = handler(event, None)
        
        # Convert response to Flask format
        from flask import Response
        return Response(
            response.get('body', ''),
            status=response.get('statusCode', 200),
            headers=response.get('headers', {})
        )
    except Exception as e:
        # Return error response
        return jsonify({
            "error": "Internal Server Error",
            "message": str(e)
        }), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    print(f"Starting server on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False)
