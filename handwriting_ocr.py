"""
handwriting_ocr.py
──────────────────
Offline handwriting recognition module using Tesseract 5 + OpenCV preprocessing.

Requirements:
    pip install pytesseract pillow opencv-python numpy
    System: sudo apt install tesseract-ocr   (or brew install tesseract on macOS)

Quick start:
    from handwriting_ocr import HandwritingOCR

    ocr = HandwritingOCR()
    result = ocr.read("my_note.png")
    print(result.text)
"""

from __future__ import annotations

import os
import warnings
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Union

import cv2
import numpy as np
import pytesseract
from PIL import Image

# ──────────────────────────────────────────────
# Public result type
# ──────────────────────────────────────────────

@dataclass
class OCRResult:
    """Returned by every HandwritingOCR.read*() call."""
    text: str                          # cleaned final text
    raw_text: str                      # text straight from Tesseract
    confidence: float                  # mean word-level confidence (0-100)
    word_data: list[dict] = field(default_factory=list)
    # each dict: {text, conf, left, top, width, height}

    def __str__(self) -> str:
        return self.text

    def __repr__(self) -> str:
        snippet = (self.text[:40] + "…") if len(self.text) > 40 else self.text
        return f"OCRResult(conf={self.confidence:.1f}, text={snippet!r})"


# ──────────────────────────────────────────────
# Core module
# ──────────────────────────────────────────────

class HandwritingOCR:
    """
    Offline handwriting / printed-text recognition.

    Parameters
    ----------
    tesseract_cmd : str or None
        Path to the tesseract binary. Auto-detected when None.
    lang : str
        Tesseract language code(s), e.g. "eng", "eng+fra".
    psm : int
        Tesseract page segmentation mode (default 6 = uniform block of text).
        Common alternatives:
          3  – fully automatic (no OSD)
          4  – single column
          6  – single uniform text block  ← default
          7  – single text line
          11 – sparse text (notes, scattered words)
          13 – raw line (good for single cursive lines)
    oem : int
        OCR engine mode. 3 = LSTM (best); 1 = LSTM only; 0 = legacy only.
    preprocess : str
        Preprocessing pipeline name: "auto" | "light" | "heavy" | "none"
        - "auto"  → chooses light or heavy based on image analysis
        - "light" → mild contrast/denoise, good for clean scans
        - "heavy" → adaptive threshold + morph ops, good for low-quality photos
        - "none"  → send image straight to Tesseract
    upscale_threshold : int
        Images narrower than this (px) are upscaled before OCR.
    """

    # Tesseract config templates
    _CONFIGS = {
        "default": "--oem {oem} --psm {psm}",
        "whitelist_alpha": "--oem {oem} --psm {psm} -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz ",
    }

    def __init__(
        self,
        tesseract_cmd: Optional[str] = None,
        lang: str = "eng",
        psm: int = 6,
        oem: int = 3,
        preprocess: str = "auto",
        upscale_threshold: int = 1000,
    ):
        if tesseract_cmd:
            pytesseract.pytesseract.tesseract_cmd = tesseract_cmd

        self.lang = lang
        self.psm = psm
        self.oem = oem
        self.preprocess = preprocess
        self.upscale_threshold = upscale_threshold

        # Verify Tesseract is reachable
        try:
            pytesseract.get_tesseract_version()
        except pytesseract.TesseractNotFoundError as exc:
            raise EnvironmentError(
                "Tesseract not found. Install it:\n"
                "  Ubuntu/Debian: sudo apt install tesseract-ocr\n"
                "  macOS:         brew install tesseract\n"
                "  Windows:       https://github.com/UB-Mannheim/tesseract/wiki\n"
                "Then pass tesseract_cmd='/path/to/tesseract' if it's not on PATH."
            ) from exc

    # ── Public API ────────────────────────────

    def read(self, source: Union[str, Path, np.ndarray, Image.Image]) -> OCRResult:
        """
        Recognise handwriting in *source*.

        Parameters
        ----------
        source : file path (str/Path), NumPy array (BGR or gray), or PIL Image.

        Returns
        -------
        OCRResult  with .text, .confidence, .word_data, .raw_text
        """
        img_bgr = self._load(source)
        processed = self._preprocess(img_bgr)
        return self._run_tesseract(processed)

    def read_line(self, source: Union[str, Path, np.ndarray, Image.Image]) -> OCRResult:
        """Optimised for a single handwritten line (sets psm=7 temporarily)."""
        saved = self.psm
        self.psm = 7
        try:
            return self.read(source)
        finally:
            self.psm = saved

    def read_word(self, source: Union[str, Path, np.ndarray, Image.Image]) -> OCRResult:
        """Optimised for a single handwritten word (sets psm=8 temporarily)."""
        saved = self.psm
        self.psm = 8
        try:
            return self.read(source)
        finally:
            self.psm = saved

    def read_sparse(self, source: Union[str, Path, np.ndarray, Image.Image]) -> OCRResult:
        """
        Good for sticky notes, scattered annotations, or form fields
        (uses psm=11 – sparse text).
        """
        saved = self.psm
        self.psm = 11
        try:
            return self.read(source)
        finally:
            self.psm = saved

    def debug_image(
        self,
        source: Union[str, Path, np.ndarray, Image.Image],
        output_path: str = "debug_preprocessed.png",
    ) -> np.ndarray:
        """
        Save the preprocessed image so you can see what Tesseract actually sees.
        Useful for tuning the pipeline.
        """
        img_bgr = self._load(source)
        processed = self._preprocess(img_bgr)
        cv2.imwrite(output_path, processed)
        print(f"[HandwritingOCR] Debug image saved → {output_path}")
        return processed

    # ── Loading ───────────────────────────────

    def _load(self, source) -> np.ndarray:
        if isinstance(source, (str, Path)):
            path = str(source)
            if not os.path.exists(path):
                raise FileNotFoundError(f"Image not found: {path}")
            img = cv2.imread(path)
            if img is None:
                raise ValueError(f"OpenCV could not read image: {path}")
            return img
        if isinstance(source, Image.Image):
            return cv2.cvtColor(np.array(source.convert("RGB")), cv2.COLOR_RGB2BGR)
        if isinstance(source, np.ndarray):
            if source.ndim == 2:                        # already grayscale
                return cv2.cvtColor(source, cv2.COLOR_GRAY2BGR)
            if source.shape[2] == 4:                    # BGRA → BGR
                return cv2.cvtColor(source, cv2.COLOR_BGRA2BGR)
            return source.copy()
        raise TypeError(f"Unsupported image type: {type(source)}")

    # ── Preprocessing ─────────────────────────

    def _preprocess(self, img_bgr: np.ndarray) -> np.ndarray:
        mode = self.preprocess
        if mode == "none":
            return img_bgr
        if mode == "auto":
            mode = self._choose_pipeline(img_bgr)
        if mode == "light":
            return self._pipeline_light(img_bgr)
        if mode == "heavy":
            return self._pipeline_heavy(img_bgr)
        warnings.warn(f"Unknown preprocess mode '{mode}', using 'light'.")
        return self._pipeline_light(img_bgr)

    def _choose_pipeline(self, img_bgr: np.ndarray) -> str:
        """Heuristic: dark/noisy → heavy; bright/clean → light."""
        gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
        mean_brightness = float(gray.mean())
        std_brightness = float(gray.std())
        # Low contrast or dark background → heavy pipeline
        if mean_brightness < 180 or std_brightness > 70:
            return "heavy"
        return "light"

    def _upscale_if_needed(self, img: np.ndarray) -> np.ndarray:
        h, w = img.shape[:2]
        if w < self.upscale_threshold:
            scale = self.upscale_threshold / w
            new_w, new_h = int(w * scale), int(h * scale)
            img = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_CUBIC)
        return img

    def _pipeline_light(self, img_bgr: np.ndarray) -> np.ndarray:
        """
        Light pipeline – good for clean scans or high-quality photos.
        Steps: upscale → grayscale → CLAHE → mild denoise → Otsu threshold
        """
        img = self._upscale_if_needed(img_bgr)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # Contrast-limited adaptive histogram equalisation
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        gray = clahe.apply(gray)

        # Mild Gaussian denoise
        gray = cv2.GaussianBlur(gray, (3, 3), 0)

        # Global Otsu threshold → binary image
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        return binary

    def _pipeline_heavy(self, img_bgr: np.ndarray) -> np.ndarray:
        """
        Heavy pipeline – good for phone photos, low lighting, shadows.
        Steps: upscale → grayscale → denoise → deskew → adaptive threshold → morph
        """
        img = self._upscale_if_needed(img_bgr)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # Strong denoise
        gray = cv2.fastNlMeansDenoising(gray, h=10, templateWindowSize=7, searchWindowSize=21)

        # Deskew
        gray = self._deskew(gray)

        # Adaptive threshold (handles uneven lighting / shadows)
        binary = cv2.adaptiveThreshold(
            gray, 255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            blockSize=31,
            C=10,
        )

        # Morphological opening to remove tiny noise specks
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
        binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel)

        # Dilate slightly to reconnect broken strokes
        kernel2 = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 1))
        binary = cv2.dilate(binary, kernel2, iterations=1)

        return binary

    def _deskew(self, gray: np.ndarray) -> np.ndarray:
        """Rotate image to straighten dominant text angle (±45°)."""
        coords = np.column_stack(np.where(gray < 128))   # dark pixels
        if len(coords) < 50:
            return gray
        angle = cv2.minAreaRect(coords)[-1]
        if angle < -45:
            angle = 90 + angle
        if abs(angle) < 0.5:   # negligible skew
            return gray
        (h, w) = gray.shape
        center = (w // 2, h // 2)
        M = cv2.getRotationMatrix2D(center, angle, 1.0)
        rotated = cv2.warpAffine(
            gray, M, (w, h),
            flags=cv2.INTER_CUBIC,
            borderMode=cv2.BORDER_REPLICATE,
        )
        return rotated

    # ── Tesseract ─────────────────────────────

    def _run_tesseract(self, img: np.ndarray) -> OCRResult:
        config = self._CONFIGS["default"].format(oem=self.oem, psm=self.psm)

        # Convert to PIL (Tesseract wrapper works best with PIL)
        if img.ndim == 2:
            pil_img = Image.fromarray(img)
        else:
            pil_img = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))

        # Raw text
        raw_text: str = pytesseract.image_to_string(pil_img, lang=self.lang, config=config)

        # Per-word data with confidence scores
        data = pytesseract.image_to_data(
            pil_img, lang=self.lang, config=config,
            output_type=pytesseract.Output.DICT,
        )

        word_data = []
        confidences = []
        for i, word in enumerate(data["text"]):
            conf = int(data["conf"][i])
            if conf < 0 or not word.strip():
                continue
            word_data.append({
                "text":   word,
                "conf":   conf,
                "left":   data["left"][i],
                "top":    data["top"][i],
                "width":  data["width"][i],
                "height": data["height"][i],
            })
            confidences.append(conf)

        mean_conf = float(np.mean(confidences)) if confidences else 0.0
        clean_text = self._clean(raw_text)

        return OCRResult(
            text=clean_text,
            raw_text=raw_text,
            confidence=mean_conf,
            word_data=word_data,
        )

    # ── Post-processing ───────────────────────

    @staticmethod
    def _clean(text: str) -> str:
        """Strip trailing whitespace per line; collapse 3+ blank lines to 2."""
        lines = [ln.rstrip() for ln in text.splitlines()]
        result, blank_count = [], 0
        for ln in lines:
            if ln == "":
                blank_count += 1
                if blank_count <= 2:
                    result.append(ln)
            else:
                blank_count = 0
                result.append(ln)
        return "\n".join(result).strip()


# ──────────────────────────────────────────────
# Convenience function
# ──────────────────────────────────────────────

def read_handwriting(
    source: Union[str, Path, np.ndarray, Image.Image],
    *,
    lang: str = "eng",
    psm: int = 6,
    preprocess: str = "auto",
) -> str:
    """
    One-liner helper. Returns recognised text as a plain string.

    Example
    -------
    >>> from handwriting_ocr import read_handwriting
    >>> text = read_handwriting("note.jpg")
    >>> print(text)
    """
    ocr = HandwritingOCR(lang=lang, psm=psm, preprocess=preprocess)
    return ocr.read(source).text


# ──────────────────────────────────────────────
# CLI  (python handwriting_ocr.py image.jpg)
# ──────────────────────────────────────────────

if __name__ == "__main__":
    import argparse, sys, json

    parser = argparse.ArgumentParser(
        description="Offline handwriting OCR",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python handwriting_ocr.py note.jpg
  python handwriting_ocr.py note.jpg --psm 7 --preprocess heavy
  python handwriting_ocr.py note.jpg --json
  python handwriting_ocr.py note.jpg --debug
""",
    )
    parser.add_argument("image", help="Path to image file")
    parser.add_argument("--lang",       default="eng",  help="Tesseract language (default: eng)")
    parser.add_argument("--psm",        default=6, type=int, help="Page segmentation mode (default: 6)")
    parser.add_argument("--oem",        default=3, type=int, help="OCR engine mode (default: 3)")
    parser.add_argument("--preprocess", default="auto",
                        choices=["auto","light","heavy","none"],
                        help="Preprocessing pipeline (default: auto)")
    parser.add_argument("--json",   action="store_true", help="Output JSON with confidence + word data")
    parser.add_argument("--debug",  action="store_true", help="Save preprocessed image as debug_preprocessed.png")
    args = parser.parse_args()

    ocr = HandwritingOCR(lang=args.lang, psm=args.psm, oem=args.oem, preprocess=args.preprocess)

    if args.debug:
        ocr.debug_image(args.image)

    result = ocr.read(args.image)

    if args.json:
        out = {
            "text":       result.text,
            "confidence": round(result.confidence, 2),
            "words":      result.word_data,
        }
        print(json.dumps(out, indent=2, ensure_ascii=False))
    else:
        print(result.text)
        print(f"\n[confidence: {result.confidence:.1f}%]", file=sys.stderr)
