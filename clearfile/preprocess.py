import numpy as np
import cv2


LOWER_THRESHOLD = 50
UPPER_THRESHOLD = 190


def crop(img, contour):
    ''' Crop an image to the bounding rectangle of a contour. '''
    x, y, w, h = cv2.boundingRect(contour)
    return img[y:y + h, x:x + w]


def prepare(img):
    '''Prepare an image for crop_to_page. Performs a Gaussian blur, then converts
    the result image to black and white. '''
    blur = cv2.GaussianBlur(img, (1, 1), 0)
    return cv2.cvtColor(blur, cv2.COLOR_BGR2GRAY)


def find_largest_rectangle(img):
    ''' Takes a (preprocessed) image and finds the largest rectangle. '''
    # Find edges with Canny edge detection
    edges = cv2.Canny(img, LOWER_THRESHOLD, UPPER_THRESHOLD)
    # Use simple edge chaining to find contours from discovered edges.
    _, contours, _ = cv2.findContours(edges, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    # Take the largest rectangular contour (by area) from the list of
    # discovered contours.
    max_contour = None
    for contour in contours:
        epsilon = 0.01 * cv2.arcLength(contour, True)
        approx = cv2.approxPolyDP(contour, epsilon, True)
        is_rectangle = len(approx) == 4
        larger_contour = True
        if max_contour is not None:
            contour_area = cv2.contourArea(contour)
            max_contour_area = cv2.contourArea(max_contour)
            larger_contour = contour_area > max_contour_area
        if is_rectangle and larger_contour:
            max_contour = contour
    return max_contour


def crop_to_page(img):
    ''' Crops an image to a page it finds within that image. The bounding
    rectangle is not minimal in size, but the background is blacked out to
    avoid tripping up OCR images. '''
    stencil = np.zeros(img.shape).astype(img.dtype)
    preprocessed = prepare(img)
    page_contour = find_largest_rectangle(preprocessed)
    cv2.fillPoly(stencil, [page_contour], (255, 255, 255))
    stencil = cv2.bitwise_and(img, stencil)
    return crop(stencil, page_contour)
