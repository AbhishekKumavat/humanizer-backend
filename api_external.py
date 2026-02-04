import os
import json
import requests
import time
from typing import Dict, Tuple
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get API token from environment
HF_API_TOKEN = os.getenv('HF_API_TOKEN', '')
API_URL_BASE = "https://api-inference.huggingface.co/models"

def call_hf_api(model_id: str, inputs: str, parameters: Dict = None) -> Dict:
    """Call Hugging Face Inference API"""
    if not HF_API_TOKEN:
        raise Exception("HF_API_TOKEN environment variable not set")
    
    headers = {"Authorization": f"Bearer {HF_API_TOKEN}"}
    API_URL = f"{API_URL_BASE}/{model_id}"
    
    payload = {
        "inputs": inputs,
        "parameters": parameters or {}
    }
    
    try:
        response = requests.post(API_URL, headers=headers, json=payload)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"API call failed: {str(e)}")
        raise

def paraphrase_text(text: str, model_name: str = None) -> Tuple[str, str]:
    """Paraphrase using external API"""
    try:
        if not model_name:
            model_name = "humarin/chatgpt_paraphraser_on_T5_base"
        
        # For paraphrasing models, we need to format the input
        formatted_input = f"paraphrase: {text}"
        
        result = call_hf_api(
            model_name, 
            formatted_input,
            {"max_length": len(text) * 2, "min_length": len(text) // 2}
        )
        
        if isinstance(result, list) and len(result) > 0:
            paraphrased = result[0].get('generated_text', text)
            return paraphrased, ""
        else:
            return text, "API returned unexpected format"
            
    except Exception as e:
        logger.error(f"Paraphrasing failed: {str(e)}")
        return text, str(e)

def rewrite_text(text: str, enhanced: bool = False) -> Tuple[str, str]:
    """Rewrite text using API-based approach"""
    try:
        # Use a text generation model for rewriting
        model = "google/flan-t5-base"  # Lighter model for rewriting
        
        prompt = f"Rewrite this text to make it more human-like and natural: {text}"
        if enhanced:
            prompt = f"Significantly rewrite and humanize this text to make it appear completely human-written: {text}"
        
        result = call_hf_api(
            model,
            prompt,
            {"max_length": len(text) * 3, "min_length": len(text)}
        )
        
        if isinstance(result, list) and len(result) > 0:
            rewritten = result[0].get('generated_text', text)
            return rewritten, ""
        else:
            return text, "API returned unexpected format"
            
    except Exception as e:
        logger.error(f"Rewriting failed: {str(e)}")
        return text, str(e)

def detect_ai_text(text: str, method: str = "ensemble") -> Dict:
    """Detect AI text using external API"""
    try:
        # Use a classifier model
        model = "roberta-base-openai-detector"
        
        result = call_hf_api(model, text)
        
        if isinstance(result, list) and len(result) > 0:
            # Parse the result (format depends on the model)
            prediction = result[0]
            if isinstance(prediction, dict):
                ai_score = prediction.get('score', 0.5) if prediction.get('label') == 'AI' else 1 - prediction.get('score', 0.5)
            else:
                ai_score = 0.5  # Default if format unknown
            
            return {
                'ensemble_ai_probability': ai_score,
                'ensemble_human_probability': 1 - ai_score,
                'prediction': 'AI-generated' if ai_score > 0.5 else 'Human-written',
                'confidence': abs(ai_score - 0.5) * 2,
                'models_used': [model]
            }
        else:
            # Default response if API fails
            return {
                'ensemble_ai_probability': 0.5,
                'ensemble_human_probability': 0.5,
                'prediction': 'Uncertain',
                'confidence': 0.0,
                'models_used': []
            }
            
    except Exception as e:
        logger.error(f"AI detection failed: {str(e)}")
        # Return neutral result on failure
        return {
            'ensemble_ai_probability': 0.5,
            'ensemble_human_probability': 0.5,
            'prediction': 'Detection failed',
            'confidence': 0.0,
            'models_used': [],
            'error': str(e)
        }

def is_ai_generated(text: str, threshold: float = 0.7) -> Tuple[bool, float]:
    """Simple AI detection check"""
    result = detect_ai_text(text)
    ai_prob = result['ensemble_ai_probability']
    confidence = result['confidence']
    return ai_prob > threshold, confidence

# Export functions for main API
__all__ = ['paraphrase_text', 'rewrite_text', 'detect_ai_text', 'is_ai_generated']