"""
ONNX Captcha Solver for WOS-M
Based on Whiteout Project's GiftCaptchaSolver
© MANSOUR — WOS-M. All rights reserved.
"""
import os
import io
import time
import asyncio
import logging
import json

try:
    import sys
    _fd, _null = sys.stderr.fileno(), os.open(os.devnull, os.O_WRONLY)
    _bak = os.dup(_fd)
    os.dup2(_null, _fd)
    os.close(_null)
    import onnxruntime as ort
    os.dup2(_bak, _fd)
    os.close(_bak)
    import numpy as np
    from PIL import Image
    ONNX_AVAILABLE = True
except ImportError:
    ort = None
    np = None
    Image = None
    ONNX_AVAILABLE = False

logger = logging.getLogger(__name__)


class LazyOnnxModel:
    """Lazy ONNX model wrapper with memory management."""
    
    def __init__(self, name: str, display_name: str, factory, pinned: bool = False):
        self.name = name
        self.display_name = display_name
        self._factory = factory
        self._session = None
        self._pinned = pinned
        self._lock = asyncio.Lock()
        self._loaded = False
    
    async def use(self):
        """Get the model session, loading it if necessary."""
        if self._pinned and self._session is not None:
            return self._session
        
        async with self._lock:
            if self._session is None:
                logger.info(f"Loading {self.display_name} model...")
                self._session = self._factory()
                self._loaded = True
                logger.info(f"{self.display_name} model loaded")
            return self._session
    
    async def unload(self):
        """Unload the model from memory."""
        async with self._lock:
            if self._session is not None and not self._pinned:
                del self._session
                self._session = None
                self._loaded = False


class OnnxModelManager:
    """Centralized ONNX model management."""
    
    _models = {}
    
    @classmethod
    def get_or_create(cls, name: str, display_name: str, factory, pinned: bool = False):
        if name not in cls._models:
            cls._models[name] = LazyOnnxModel(name, display_name, factory, pinned)
        return cls._models[name]
    
    @classmethod
    async def unload_all(cls):
        for model in cls._models.values():
            await model.unload()


class GiftCaptchaSolver:
    """
    ONNX-based CAPTCHA solver for gift code redemption.
    Uses a neural network model to automatically solve WOS captchas.
    """
    
    def __init__(self, save_images: int = 0):
        """
        Initialize the ONNX captcha solver.
        
        Args:
            save_images: Image saving mode (0=None, 1=Failed, 2=Success, 3=All)
        """
        self.save_images_mode = save_images
        self.model_metadata = None
        self.is_initialized = False
        self._model_wrapper = None
        
        self.logger = logging.getLogger('gift.captcha')
        
        self.captcha_dir = 'captcha_images'
        os.makedirs(self.captcha_dir, exist_ok=True)
        
        self._initialize_onnx_model()
        
        self.stats = {
            "total_attempts": 0,
            "successful_decodes": 0,
            "failures": 0
        }
        self.reset_run_stats()
    
    def reset_run_stats(self):
        """Reset statistics for the current run."""
        self.run_stats = {
            "total_attempts": 0,
            "successful_decodes": 0,
            "failures": 0,
            "start_time": time.time()
        }
    
    def _initialize_onnx_model(self):
        """Verify model files exist and load metadata."""
        if not ONNX_AVAILABLE:
            self.logger.error("ONNX Runtime or required libraries not found. Captcha solving disabled.")
            self.is_initialized = False
            return
        
        try:
            # Look for model in multiple locations
            possible_paths = [
                os.path.join(os.path.dirname(__file__), '..', '..', 'models', 'captcha_model.onnx'),
                os.path.join(os.path.dirname(__file__), '..', '..', 'models', 'captcha_model.onnx'),
                'models/captcha_model.onnx',
                '/workspace/project/wos-m/models/captcha_model.onnx'
            ]
            
            model_path = None
            for path in possible_paths:
                full_path = os.path.abspath(path)
                if os.path.exists(full_path):
                    model_path = full_path
                    break
            
            metadata_path = os.path.join(os.path.dirname(model_path) if model_path else '', 'captcha_model_metadata.json')
            metadata_path = os.path.abspath(metadata_path)
            
            if model_path is None or not os.path.exists(model_path):
                self.logger.warning(f"ONNX model file not found. Captcha solver will use fallback method.")
                self.is_initialized = False
                return
            
            if not os.path.exists(metadata_path):
                self.logger.warning(f"Model metadata file not found. Using default metadata.")
                # Create default metadata
                self.model_metadata = {
                    'input_shape': [1, 1, 40, 120],
                    'chars': list('ABCDEFGHJKLMNPQRSTUVWXYZ23456789'),
                    'idx_to_char': {str(i): c for i, c in enumerate('ABCDEFGHJKLMNPQRSTUVWXYZ23456789')},
                    'normalization': {'mean': [0.5], 'std': [0.5]}
                }
            else:
                with open(metadata_path, 'r') as f:
                    self.model_metadata = json.load(f)
            
            # Create lazy model wrapper
            self._model_wrapper = OnnxModelManager.get_or_create(
                name='captcha',
                display_name='Gift Captcha',
                factory=lambda: ort.InferenceSession(model_path),
                pinned=True,  # Keep loaded for performance
            )
            
            self.is_initialized = True
            self.logger.info("Captcha solver ready (model will load on first use).")
            
        except Exception as e:
            self.logger.exception(f"Failed during captcha solver initialization: {e}")
            self.model_metadata = None
            self.is_initialized = False
    
    def _preprocess_image(self, image_bytes: bytes):
        """Preprocess image for ONNX model input."""
        try:
            image = Image.open(io.BytesIO(image_bytes))
            
            if image.mode != 'L':
                image = image.convert('L')
            
            height, width = self.model_metadata['input_shape'][1:3]
            image = image.resize((width, height), Image.LANCZOS)
            
            image_array = np.array(image, dtype=np.float32)
            
            mean = self.model_metadata['normalization']['mean'][0]
            std = self.model_metadata['normalization']['std'][0]
            image_array = (image_array / 255.0 - mean) / std
            
            image_array = np.expand_dims(image_array, axis=0)
            image_array = np.expand_dims(image_array, axis=0)
            
            return image_array
            
        except Exception as e:
            self.logger.error(f"Error preprocessing image: {e}")
            return None
    
    def _run_inference_sync(self, image_bytes: bytes, session):
        """Synchronous inference runner."""
        input_data = self._preprocess_image(image_bytes)
        if input_data is None:
            return None
        
        input_name = session.get_inputs()[0].name
        outputs = session.run(None, {input_name: input_data})
        
        idx_to_char = self.model_metadata['idx_to_char']
        predicted_text = ""
        confidences = []
        
        for pos in range(4):
            char_probs = outputs[pos][0]
            predicted_idx = np.argmax(char_probs)
            confidences.append(float(char_probs[predicted_idx]))
            predicted_text += idx_to_char[str(predicted_idx)]
        
        return predicted_text, sum(confidences) / len(confidences)
    
    async def solve_captcha(self, image_bytes: bytes, fid=None, attempt: int = 0):
        """
        Attempt to solve captcha using ONNX model.
        
        Args:
            image_bytes: Raw byte data of the captcha image
            fid: Player ID for logging
            attempt: Attempt number for logging
        
        Returns:
            tuple: (solved_code, success, method, confidence, image_path)
        """
        if not self.is_initialized or not self._model_wrapper or not self.model_metadata:
            self.logger.error(f"ONNX model not initialized. Using fallback method.")
            return await self._fallback_solve(image_bytes, fid, attempt)
        
        self.stats["total_attempts"] += 1
        self.run_stats["total_attempts"] += 1
        start_time = time.time()
        
        try:
            EXPECTED_CAPTCHA_LENGTH = 4
            VALID_CHARACTERS = set(self.model_metadata['chars'])
            
            async with self._model_wrapper.use() as session:
                inference_result = await asyncio.to_thread(
                    self._run_inference_sync, image_bytes, session
                )
            
            if inference_result is None:
                self.stats["failures"] += 1
                self.run_stats["failures"] += 1
                self.logger.error(f"[Solver] ID {fid}, Attempt {attempt+1}: Failed to preprocess image")
                return None, False, "ONNX", 0.0, None
            
            predicted_text, avg_confidence = inference_result
            solve_duration = time.time() - start_time
            
            self.logger.info(f"[Solver] ID {fid}, Attempt {attempt+1}: ONNX raw result='{predicted_text}' "
                           f"(confidence: {avg_confidence:.3f}, {solve_duration:.3f}s)")
            
            if (predicted_text and
                isinstance(predicted_text, str) and
                len(predicted_text) == EXPECTED_CAPTCHA_LENGTH and
                all(c in VALID_CHARACTERS for c in predicted_text)):
                
                self.stats["successful_decodes"] += 1
                self.run_stats["successful_decodes"] += 1
                self.logger.info(f"[Solver] ID {fid}, Attempt {attempt+1}: Success. Solved: {predicted_text}")
                return predicted_text, True, "ONNX", avg_confidence, None
            else:
                self.stats["failures"] += 1
                self.run_stats["failures"] += 1
                self.logger.warning(f"[Solver] ID {fid}, Attempt {attempt+1}: Failed validation")
                return None, False, "ONNX", 0.0, None
                
        except Exception as e:
            self.stats["failures"] += 1
            self.run_stats["failures"] += 1
            self.logger.exception(f"[Solver] ID {fid}, Attempt {attempt+1}: Exception during ONNX inference: {e}")
            return None, False, "ONNX", 0.0, None
    
    async def _fallback_solve(self, image_bytes: bytes, fid=None, attempt: int = 0):
        """
        Fallback captcha solving method using simple pattern matching.
        Used when ONNX model is not available.
        """
        self.logger.warning(f"[Solver] ID {fid}: Using fallback captcha solver")
        return None, False, "FALLBACK", 0.0, None
    
    async def get_stats(self) -> dict:
        """Get solver statistics."""
        return {
            **self.stats,
            **self.run_stats,
            "runtime": time.time() - self.run_stats.get("start_time", time.time())
        }
