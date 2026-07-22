"""
Face filter — проверяет изображение на наличие лиц через OpenCV.
Использует каскад Хаара (встроен в opencv, не нужен интернет).
"""

import cv2
import numpy as np
import requests
import os
from typing import Optional

# Загружаем каскад Хаара для лиц
_CASCADE_PATH = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
_face_cascade = cv2.CascadeClassifier(_CASCADE_PATH)


def download_image(url: str, timeout: int = 10) -> Optional[np.ndarray]:
    """Скачивает картинку по URL, возвращает numpy array или None."""
    if not url:
        return None
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(url, headers=headers, timeout=timeout, stream=True)
        if r.status_code != 200:
            return None
        arr = np.frombuffer(r.content, dtype=np.uint8)
        img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        return img
    except Exception:
        return None


def load_image_from_file(path: str) -> Optional[np.ndarray]:
    """Загружает картинку с диска."""
    try:
        return cv2.imread(path)
    except Exception:
        return None


def has_face(img: np.ndarray, min_confidence: float = 1.1,
             min_neighbors: int = 4) -> bool:
    """
    Возвращает True если на изображении найдено хотя бы одно лицо.
    min_confidence (scaleFactor): 1.05 — чувствительнее, больше ложных; 
                                   1.2  — строже, меньше ложных.
    min_neighbors: чем больше — тем строже фильтр.
    """
    if img is None:
        return False
    gray  = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    faces = _face_cascade.detectMultiScale(
        gray,
        scaleFactor  = min_confidence,
        minNeighbors = min_neighbors,
        minSize      = (30, 30),
    )
    return len(faces) > 0


def check_url(url: str) -> dict:
    """
    Проверяет URL картинки на наличие лица.
    Возвращает: {has_face: bool, error: str|None}
    """
    img = download_image(url)
    if img is None:
        return {"has_face": False, "error": "Не удалось загрузить изображение"}
    return {"has_face": has_face(img), "error": None}


def check_file(path: str) -> dict:
    """
    Проверяет файл на наличие лица.
    Возвращает: {has_face: bool, error: str|None}
    """
    img = load_image_from_file(path)
    if img is None:
        return {"has_face": False, "error": "Не удалось открыть файл"}
    return {"has_face": has_face(img), "error": None}
