import os
import logging
from datetime import datetime
from flask import Flask, jsonify, request
from flask_cors import CORS

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Enable CORS for specific frontend domains
CORS(app, origins=[
    "https://humanizer-front-klel.vercel.app",  # Production frontend
    "http://localhost:5173",                   # Local development
    "http://localhost:4173",                   # Local preview
    "http://127.0.0.1:5173",                  # Alternative local dev
    "http://127.0.0.1:4173"                   # Alternative local preview
])

@app.route('/health')
def health_check():
    """Health check endpoint"""
    logger.info("Health check requested")
    return jsonify({
        'status': 'healthy',
        'service': 'humanizer-backend',
        'timestamp': datetime.utcnow().isoformat() + 'Z'
    })

@app.route('/models')
def get_models():
    """Return available paraphrasing models"""
    try:
        logger.info("Models list requested")
        # Import here to avoid circular imports
        from paraphraser import get_available_models
        models = get_available_models()
        return jsonify({
            'status': 'success',
            'models': models,
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        })
    except Exception as e:
        logger.error(f"Error getting models: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e),
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        }), 500

@app.route('/detect_models')
def get_detect_models():
    """Return available detection models"""
    try:
        logger.info("Detection models list requested")
        # Import here to avoid circular imports
        from detector import get_available_models as get_detection_models
        models = get_detection_models()
        return jsonify({
            'status': 'success',
            'models': models,
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        })
    except Exception as e:
        logger.error(f"Error getting detection models: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e),
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        }), 500

@app.errorhandler(Exception)
def handle_exception(e):
    """Global exception handler"""
    logger.error(f"Unhandled exception: {str(e)}", exc_info=True)
    return jsonify({
        'error': 'Internal Server Error',
        'message': str(e),
        'timestamp': datetime.utcnow().isoformat() + 'Z'
    }), 500

@app.errorhandler(404)
def handle_not_found(e):
    """Handle 404 errors"""
    logger.warning(f"404 error: {request.url}")
    return jsonify({
        'error': 'Not Found',
        'message': 'Endpoint not found',
        'timestamp': datetime.utcnow().isoformat() + 'Z'
    }), 404
@app.route('/')
def home():
    """Home endpoint with API information"""
    logger.info("Home page requested")
    return jsonify({
        "status": "running", 
        "message": "Humanizer Backend API",
        "service": "humanizer-backend",
        "version": "1.0.0",
        "available_endpoints": [
            "/health",
            "/models", 
            "/detect_models",
            "/paraphrase",
            "/detect",
            "/rewrite"
        ],
        "timestamp": datetime.utcnow().isoformat() + 'Z'
    })

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
    logger.info(f"Starting Humanizer Backend server on port {port}")
    logger.info(f"CORS enabled for domains: https://humanizer-front-klel.vercel.app, http://localhost:5173, http://localhost:4173")
    app.run(host='0.0.0.0', port=port, debug=False)
