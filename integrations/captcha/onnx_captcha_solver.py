"""
ONNX Captcha Solver for Gift Code Redemption.
Based on: https://github.com/whiteout-project/bot

Uses a custom ONNX neural network model for captcha solving.
"""
import os
import io
import time
import asyncio
import logging
import json
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

ONNX_AVAILABLE = False
ort = None
np = None
Image = None

try:
    import sys
    import onnxruntime as ort
    import numpy as np
    from PIL import Image
    ONNX_AVAILABLE = True
except ImportError:
    logger.warning("ONNX Runtime not installed. Using fallback solver.")
    ort = None
    np = None
    Image = None
except Exception as e:
    logger.warning(f"ONNX Runtime initialization failed: {e}. Using fallback solver.")
    ort = None
    np = None
    Image = None

from integrations.captcha.onnx_lifecycle import get_or_create


class OnnxCaptchaSolver:
    """
    ONNX-based captcha solver.
    
    Uses a neural network model to solve captcha images.
    Falls back to ddddocr if ONNX is not available.
    """
    
    MIN_CONFIDENCE = 0.60
    EXPECTED_CAPTCHA_LENGTH = 4
    
    def __init__(self, save_images: int = 0):
        """
        Initialize the ONNX captcha solver.
        
        Args:
            save_images: Image saving mode (0=None, 1=Failed, 2=Success, 3=All)
        """
        self.save_images_mode = save_images
        self.model_metadata: Optional[dict] = None
        self.is_initialized: bool = False
        self._model_wrapper = None
        self._ddddocr_fallback = None
        self._ddddocr_available = False
        
        self._initialize_onnx_model()
        self._initialize_ddddocr_fallback()
        
        self.stats = {
            "total_attempts": 0,
            "successful_decodes": 0,
            "failures": 0,
            "onnx_attempts": 0,
            "ddddocr_attempts": 0,
        }
    
    def _initialize_onnx_model(self):
        """Initialize ONNX model and load metadata."""
        if not ONNX_AVAILABLE:
            logger.warning("ONNX Runtime not available")
            return
        
        try:
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            models_dir = os.path.join(base_dir, 'models')
            model_path = os.path.join(models_dir, 'captcha_model.onnx')
            metadata_path = os.path.join(models_dir, 'captcha_model_metadata.json')
            
            if not os.path.exists(model_path):
                logger.warning(f"ONNX model not found at {model_path}")
                return
            if not os.path.exists(metadata_path):
                logger.warning(f"Model metadata not found at {metadata_path}")
                return
            
            with open(metadata_path, 'r') as f:
                self.model_metadata = json.load(f)
            
            self._model_wrapper = get_or_create(
                name='captcha',
                display_name='Gift Captcha',
                factory=lambda: ort.InferenceSession(model_path),
                pinned=True,
            )
            self.is_initialized = True
            logger.info("ONNX Captcha solver ready (model loads on first use)")
            
        except Exception as e:
            logger.error(f"ONNX model initialization failed: {e}")
            self.model_metadata = None
            self.is_initialized = False
    
    def _initialize_ddddocr_fallback(self):
        """Initialize ddddocr as fallback."""
        try:
            import ddddocr
            self._ddddocr_fallback = ddddocr.DdddOcr(show_ad=False)
            self._ddddocr_available = True
            logger.info("ddddocr fallback available")
        except ImportError:
            self._ddddocr_fallback = None
            self._ddddocr_available = False
    
    def _preprocess_image(self, image_bytes: bytes) -> Optional["np.ndarray"]:
        """Preprocess image for ONNX model input."""
        if np is None:
            return None
        if not self.model_metadata:
            return None
        
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
            logger.error(f"Image preprocessing error: {e}")
            return None
    
    def _run_inference_sync(self, image_bytes: bytes, session) -> Optional[Tuple[str, float]]:
        """Run ONNX inference synchronously."""
        if np is None:
            return None
        input_data = self._preprocess_image(image_bytes)
        if input_data is None:
            return None
        
        input_name = session.get_inputs()[0].name
        outputs = session.run(None, {input_name: input_data})
        
        idx_to_char = self.model_metadata['idx_to_char']
        predicted_text = ""
        confidences = []
        
        for pos in range(self.EXPECTED_CAPTCHA_LENGTH):
            char_probs = outputs[pos][0]
            predicted_idx = np.argmax(char_probs)
            confidences.append(float(char_probs[predicted_idx]))
            predicted_text += idx_to_char[str(predicted_idx)]
        
        return predicted_text, sum(confidences) / len(confidences)
    
    def _solve_with_ddddocr(self, image_bytes: bytes) -> Tuple[Optional[str], float]:
        """Solve captcha using ddddocr fallback."""
        if not self._ddddocr_available or not self._ddddocr_fallback:
            return None, 0.0
        
        try:
            result = self._ddddocr_fallback.classification(image_bytes)
            if result:
                return result, 0.75
            return None, 0.0
        except Exception as e:
            logger.error(f"ddddocr error: {e}")
            return None, 0.0
    
    async def solve_captcha(
        self,
        image_bytes: bytes,
        fid: str = None,
        attempt: int = 0
    ) -> Tuple[Optional[str], bool, str, float, Optional[str]]:
        """
        Solve captcha using ONNX model.
        
        Args:
            image_bytes: Raw captcha image data
            fid: Player ID for logging
            attempt: Attempt number
            
        Returns:
            Tuple: (solved_code, success, method, confidence, image_path)
        """
        self.stats["total_attempts"] += 1
        start_time = time.time()
        
        logger.info(f"[Solver] ID {fid}, Attempt {attempt + 1}: Starting captcha solve")
        
        if self.is_initialized and self._model_wrapper and self.model_metadata:
            result = await self._solve_with_onnx(image_bytes, fid, attempt)
            if result[1]:
                self.stats["onnx_attempts"] += 1
                return result
        
        self.stats["ddddocr_attempts"] += 1
        return await self._solve_with_ddddocr_async(image_bytes, fid, attempt)
    
    async def _solve_with_onnx(
        self,
        image_bytes: bytes,
        fid: str,
        attempt: int
    ) -> Tuple[Optional[str], bool, str, float, Optional[str]]:
        """Solve captcha using ONNX model."""
        start_time = time.time()
        try:
            async with self._model_wrapper.use() as session:
                inference_result = await asyncio.to_thread(
                    self._run_inference_sync, image_bytes, session
                )
            
            if inference_result is None:
                logger.error(f"[Solver] ID {fid}, Attempt {attempt + 1}: Preprocess failed")
                return None, False, "ONNX", 0.0, None
            
            predicted_text, avg_confidence = inference_result
            solve_duration = time.time() - start_time
            
            logger.info(
                f"[Solver] ID {fid}, Attempt {attempt + 1}: "
                f"ONNX result='{predicted_text}' (confidence: {avg_confidence:.3f}, {solve_duration:.3f}s)"
            )
            
            VALID_CHARACTERS = set(self.model_metadata['chars'])
            
            if (predicted_text and
                isinstance(predicted_text, str) and
                len(predicted_text) == self.EXPECTED_CAPTCHA_LENGTH and
                all(c in VALID_CHARACTERS for c in predicted_text)):
                
                self.stats["successful_decodes"] += 1
                logger.info(f"[Solver] ID {fid}, Attempt {attempt + 1}: ONNX success")
                return predicted_text, True, "ONNX", avg_confidence, None
            else:
                self.stats["failures"] += 1
                logger.warning(
                    f"[Solver] ID {fid}, Attempt {attempt + 1}: "
                    f"ONNX validation failed (len={len(predicted_text) if predicted_text else 'N/A'})"
                )
                return None, False, "ONNX", 0.0, None
                
        except Exception as e:
            logger.exception(f"[Solver] ID {fid}, Attempt {attempt + 1}: ONNX exception: {e}")
            self.stats["failures"] += 1
            return None, False, "ONNX", 0.0, None
    
    async def _solve_with_ddddocr_async(
        self,
        image_bytes: bytes,
        fid: str,
        attempt: int
    ) -> Tuple[Optional[str], bool, str, float, Optional[str]]:
        """Solve captcha using ddddocr fallback."""
        if not self._ddddocr_available:
            logger.warning(f"[Solver] ID {fid}: No solver available")
            return None, False, "NONE", 0.0, None
        
        try:
            solved = await asyncio.to_thread(self._solve_with_ddddocr, image_bytes)
            predicted_text, confidence = solved
            
            if predicted_text:
                self.stats["successful_decodes"] += 1
                logger.info(f"[Solver] ID {fid}, Attempt {attempt + 1}: ddddocr success: {predicted_text}")
                return predicted_text, True, "DDDDOCR", confidence, None
            
            self.stats["failures"] += 1
            return None, False, "DDDDOCR", 0.0, None
            
        except Exception as e:
            logger.error(f"[Solver] ID {fid}: ddddocr error: {e}")
            self.stats["failures"] += 1
            return None, False, "DDDDOCR", 0.0, None
    
    def get_stats(self) -> dict:
        """Get solver statistics."""
        return self.stats.copy()
    
    def is_onnx_available(self) -> bool:
        """Check if ONNX solver is available."""
        return self.is_initialized
    
    def is_ddddocr_available(self) -> bool:
        """Check if ddddocr fallback is available."""
        return self._ddddocr_available
