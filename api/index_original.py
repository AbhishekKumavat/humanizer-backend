import os
import json
import time
from typing import Dict, Tuple
import logging
import re

# Import our utility modules
try:
    from paraphraser import paraphrase_text, load_model, get_available_models, get_current_model, get_device_info
    from rewriter import rewrite_text, get_synonym, refine_text
    from detector import (
        AITextDetector, 
        detect_with_all_models, 
        detect_with_selected_models, 
        detect_with_top_models,
        get_available_models as get_detection_models,
        get_ai_lines,
        get_ai_sentences,
        highlight_ai_text,
        detect_ai_text,
        is_ai_generated
    )
    IMPORTS_AVAILABLE = True
except ImportError as e:
    logging.error(f"Import error: {e}")
    IMPORTS_AVAILABLE = False

def clean_final_text(text: str) -> str:
    """
    Clean the final text by:
    1. Replacing every "—" with ", "
    2. Removing spaces that appear before "," or "."
    """
    if not text:
        return text
    
    # Step 1: Replace em dashes with commas
    cleaned_text = text.replace("—", ", ")
    
    # Step 2: Remove spaces before commas and periods
    cleaned_text = re.sub(r' +([,.])', r'\1', cleaned_text)
    
    return cleaned_text

class HumanizerService:
    """Main orchestrator service that combines paraphrasing and rewriting"""
    
    def __init__(self):
        logging.info("HumanizerService initialized")
    
    def humanize_text(
        self, 
        text: str, 
        use_paraphrasing: bool = True,
        use_enhanced_rewriting: bool = False,
        paraphrase_model: str = None
    ) -> Tuple[str, Dict]:
        """
        Complete text humanization pipeline:
        1. Paraphrase the text (optional)
        2. Rewrite and refine the result
        3. Clean the final text
        """
        
        if not IMPORTS_AVAILABLE:
            return text, {"error": "Required modules not available", "success": False}
        
        stats = {
            "original_length": len(text),
            "paraphrasing_used": False,
            "enhanced_rewriting_used": use_enhanced_rewriting,
            "model_used": None,
            "processing_steps": []
        }
        
        try:
            current_text = text
            
            # Step 1: Paraphrasing (if enabled)
            if use_paraphrasing:
                logging.info("Starting paraphrasing step")
                paraphrased, err = paraphrase_text(current_text, paraphrase_model)
                
                if not err and paraphrased and paraphrased.strip():
                    current_text = paraphrased
                    stats["paraphrasing_used"] = True
                    stats["model_used"] = get_current_model()
                    stats["processing_steps"].append("paraphrasing")
                    logging.info("Paraphrasing successful")
                    
                    if current_text.startswith(": "):
                        current_text = current_text[2:]
                else:
                    logging.warning(f"Paraphrasing failed or skipped: {err}")
                    stats["processing_steps"].append("paraphrasing_failed")
            
            # Step 2: Rewriting and refinement
            logging.info("Starting rewriting step")
            final_text, err = rewrite_text(current_text, enhanced=use_enhanced_rewriting)
            
            if err:
                logging.warning(f"Rewriting failed: {err}")
                final_text = current_text
                stats["processing_steps"].append("rewriting_failed")
            else:
                stats["processing_steps"].append("rewriting")
            
            # Step 3: Clean the final text
            logging.info("Cleaning final text")
            final_text = clean_final_text(final_text)
            stats["processing_steps"].append("text_cleaning")
            
            stats["final_length"] = len(final_text)
            stats["length_change"] = stats["final_length"] - stats["original_length"]
            
            return final_text, stats
            
        except Exception as e:
            logging.error(f"Error in humanization pipeline: {str(e)}")
            return text, {
                **stats,
                "error": str(e),
                "processing_steps": stats["processing_steps"] + ["error"]
            }

# Initialize services
if IMPORTS_AVAILABLE:
    humanizer_service = HumanizerService()
    ai_detector = AITextDetector()
else:
    humanizer_service = None
    ai_detector = None

def handler(event, context):
    """Main Vercel serverless function handler"""
    
    # Set CORS headers
    headers = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type',
        'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
        'Content-Type': 'application/json'
    }
    
    # Handle preflight requests
    if event.get('httpMethod') == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': headers,
            'body': ''
        }
    
    # Parse the request
    try:
        if event.get('body'):
            if isinstance(event['body'], str):
                body = json.loads(event['body'])
            else:
                body = event['body']
        else:
            body = {}
    except:
        body = {}
    
    path = event.get('path', '').rstrip('/')
    method = event.get('httpMethod', 'GET')
    
    # Route handling
    try:
        if path == '/' and method == 'GET':
            # Health check
            if not IMPORTS_AVAILABLE:
                return {
                    'statusCode': 500,
                    'headers': headers,
                    'body': json.dumps({
                        "status": "error",
                        "message": "Required modules not available",
                        "features": {
                            "paraphrasing": False,
                            "current_model": None,
                            "available_models": [],
                            "local_refinement": False,
                            "synonym_support": False
                        }
                    })
                }
            
            current_model = get_current_model()
            return {
                'statusCode': 200,
                'headers': headers,
                'body': json.dumps({
                    "status": "healthy",
                    "message": "🚀 Humanize AI Server is running!",
                    "features": {
                        "paraphrasing": current_model is not None,
                        "current_model": current_model,
                        "available_models": get_available_models(),
                        "local_refinement": True,
                        "synonym_support": True,
                        "device": get_device_info()
                    }
                })
            }
        
        elif path == '/health' and method == 'GET':
            if not IMPORTS_AVAILABLE:
                return {
                    'statusCode': 500,
                    'headers': headers,
                    'body': json.dumps({
                        "status": "error",
                        "message": "Required modules not available"
                    })
                }
            
            current_model = get_current_model()
            return {
                'statusCode': 200,
                'headers': headers,
                'body': json.dumps({
                    "status": "healthy",
                    "timestamp": time.time(),
                    "features": {
                        "paraphrasing_available": current_model is not None,
                        "current_paraphrase_model": current_model,
                        "local_processing": True,
                        "device": get_device_info()
                    },
                    "version": "3.0.0"
                })
            }
        
        elif path == '/models' and method == 'GET':
            if not IMPORTS_AVAILABLE:
                return {
                    'statusCode': 500,
                    'headers': headers,
                    'body': json.dumps({
                        "error": "Required modules not available"
                    })
                }
            
            return {
                'statusCode': 200,
                'headers': headers,
                'body': json.dumps({
                    "available_models": get_available_models(),
                    "current_model": get_current_model(),
                    "device": get_device_info()
                })
            }
        
        elif path == '/humanize' and method == 'POST':
            if not IMPORTS_AVAILABLE:
                return {
                    'statusCode': 500,
                    'headers': headers,
                    'body': json.dumps({
                        "error": "Required modules not available",
                        "success": False
                    })
                }
            
            # Validate request
            if "text" not in body:
                return {
                    'statusCode': 400,
                    'headers': headers,
                    'body': json.dumps({"error": "Text field is required"})
                }
            
            text = body.get("text", "").strip()
            if not text:
                return {
                    'statusCode': 400,
                    'headers': headers,
                    'body': json.dumps({"error": "Text cannot be empty"})
                }
            
            if len(text) < 10:
                return {
                    'statusCode': 400,
                    'headers': headers,
                    'body': json.dumps({"error": "Text must be at least 10 characters long"})
                }
            
            if len(text) > 50000:
                return {
                    'statusCode': 400,
                    'headers': headers,
                    'body': json.dumps({"error": "Text must be less than 50000 characters"})
                }
            
            # Extract options
            use_paraphrasing = body.get("paraphrasing", True)
            use_enhanced = body.get("enhanced", True)
            paraphrase_model = body.get("model", None)
            
            # Process text
            humanized_text, stats = humanizer_service.humanize_text(
                text=text,
                use_paraphrasing=use_paraphrasing,
                use_enhanced_rewriting=use_enhanced,
                paraphrase_model=paraphrase_model
            )
            
            if not humanized_text or not humanized_text.strip():
                humanized_text = text
            
            return {
                'statusCode': 200,
                'headers': headers,
                'body': json.dumps({
                    "humanized_text": humanized_text,
                    "success": True,
                    "statistics": stats
                })
            }
        
        elif path == '/detect' and method == 'POST':
            if not IMPORTS_AVAILABLE:
                return {
                    'statusCode': 500,
                    'headers': headers,
                    'body': json.dumps({
                        "error": "Required modules not available",
                        "success": False
                    })
                }
            
            text = body.get('text', '').strip()
            threshold = body.get('threshold', 0.7)
            
            if not text:
                return {
                    'statusCode': 400,
                    'headers': headers,
                    'body': json.dumps({"error": "No text provided"})
                }
            
            if len(text) < 20:
                return {
                    'statusCode': 400,
                    'headers': headers,
                    'body': json.dumps({"error": "Text must be at least 20 characters long"})
                }
            
            if len(text) > 50000:
                return {
                    'statusCode': 400,
                    'headers': headers,
                    'body': json.dumps({"error": "Text must be less than 50,000 characters"})
                }
            
            # Default ensemble method
            detector = AITextDetector()
            result = detector.detect_ensemble(text)
            is_ai = result['ensemble_ai_probability'] > threshold
            
            response = {
                "text_preview": text[:100] + "..." if len(text) > 100 else text,
                "is_ai_generated": is_ai,
                "ai_probability": result['ensemble_ai_probability'],
                "human_probability": result['ensemble_human_probability'],
                "prediction": result['prediction'],
                "confidence": result['confidence'],
                "threshold_used": threshold,
                "models_used": result['models_used'],
                "individual_results": result['individual_results'],
                "text_length": len(text),
                "detection_method": "default",
                "success": True
            }
            
            return {
                'statusCode': 200,
                'headers': headers,
                'body': json.dumps(response)
            }
        
        elif path == '/humanize_and_check' and method == 'POST':
            if not IMPORTS_AVAILABLE:
                return {
                    'statusCode': 500,
                    'headers': headers,
                    'body': json.dumps({
                        "error": "Required modules not available",
                        "success": False
                    })
                }
            
            text = body.get('text', '').strip()
            
            if not text:
                return {
                    'statusCode': 400,
                    'headers': headers,
                    'body': json.dumps({"error": "No text provided"})
                }
            
            if len(text) < 10:
                return {
                    'statusCode': 400,
                    'headers': headers,
                    'body': json.dumps({"error": "Text must be at least 10 characters long"})
                }
            
            if len(text) > 50000:
                return {
                    'statusCode': 400,
                    'headers': headers,
                    'body': json.dumps({"error": "Text must be less than 50000 characters"})
                }
            
            # Extract options
            use_paraphrasing = body.get("paraphrasing", True)
            use_enhanced = body.get("enhanced", True)
            paraphrase_model = body.get("model", None)
            detection_threshold = body.get("detection_threshold", 0.7)
            
            # Step 1: Check original text
            original_detection = detect_ai_text(text, method="ensemble")
            original_is_ai, original_confidence = is_ai_generated(text, detection_threshold)
            
            # Step 2: Humanize the text
            humanized_text, humanization_stats = humanizer_service.humanize_text(
                text=text,
                use_paraphrasing=use_paraphrasing,
                use_enhanced_rewriting=use_enhanced,
                paraphrase_model=paraphrase_model
            )
            
            # Step 3: Check humanized text
            humanized_detection = detect_ai_text(humanized_text, method="ensemble")
            humanized_is_ai, humanized_confidence = is_ai_generated(humanized_text, detection_threshold)
            
            # Calculate improvement
            ai_prob_reduction = original_detection['ensemble_ai_probability'] - humanized_detection['ensemble_ai_probability']
            detection_improved = original_is_ai and not humanized_is_ai
            
            response = {
                "original_text": text,
                "humanized_text": humanized_text,
                "humanization_stats": humanization_stats,
                "original_detection": {
                    "is_ai_generated": original_is_ai,
                    "ai_probability": original_detection['ensemble_ai_probability'],
                    "prediction": original_detection['prediction'],
                    "confidence": original_confidence
                },
                "humanized_detection": {
                    "is_ai_generated": humanized_is_ai,
                    "ai_probability": humanized_detection['ensemble_ai_probability'],
                    "prediction": humanized_detection['prediction'],
                    "confidence": humanized_confidence
                },
                "improvement": {
                    "detection_improved": detection_improved,
                    "ai_probability_reduction": ai_prob_reduction,
                    "percentage_improvement": (ai_prob_reduction / original_detection['ensemble_ai_probability'] * 100) if original_detection['ensemble_ai_probability'] > 0 else 0
                },
                "threshold_used": detection_threshold,
                "success": True
            }
            
            return {
                'statusCode': 200,
                'headers': headers,
                'body': json.dumps(response)
            }
        
        else:
            # 404 for unknown routes
            return {
                'statusCode': 404,
                'headers': headers,
                'body': json.dumps({"error": "Endpoint not found"})
            }
    
    except Exception as e:
        logging.error(f"Error processing request: {str(e)}")
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({
                "error": "Internal server error",
                "success": False
            })
        }