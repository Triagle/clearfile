import cv2
import numpy as np
import pytesseract
from PIL import Image


def scan(img, **tesseract_opts):
    img = np.array(img)
    grey = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
    thresholded = cv2.adaptiveThreshold(grey,
                                        255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                        cv2.THRESH_BINARY_INV, 11, 10)
    ocr_text = pytesseract.image_to_string(Image.fromarray(thresholded),
                                           **tesseract_opts)
    return ocr_text
