import math
import numpy as np
import cv2
import numpy as np

LOWER_THRESHOLD = 50
UPPER_THRESHOLD = 190


def crop(img, contour, xpad=100, ypad=100):
    ''' Crop an image to the bounding rectangle of a contour. '''
    x, y, w, h = cv2.boundingRect(contour)
    y = y - ypad
    x = x - xpad
    return img[y:y + h + 2 * ypad, x:x + w + 2 * xpad]


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
    max_approx = None
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
            max_approx = approx
    return max_approx, max_contour


def get_points(approx_contour):
    approx_pts = approx_contour.reshape(4, 2)
    rect = np.zeros((4, 2), dtype = "float32")

    # the top-left point has the smallest sum whereas the
    # bottom-right has the largest sum
    s = approx_pts.sum(axis=1)
    rect[0] = approx_pts[np.argmin(s)]
    rect[2] = approx_pts[np.argmax(s)]

    # compute the difference between the points -- the top-right
    # will have the minumum difference and the bottom-left will
    # have the maximum difference
    diff = np.diff(approx_pts, axis=1)
    rect[1] = approx_pts[np.argmin(diff)]
    rect[3] = approx_pts[np.argmax(diff)]
    return rect


def get_dimensions(rect):
    (tl, tr, br, bl) = rect
    widthA = np.sqrt(((br[0] - bl[0]) ** 2) + ((br[1] - bl[1]) ** 2))
    widthB = np.sqrt(((tr[0] - tl[0]) ** 2) + ((tr[1] - tl[1]) ** 2))
    heightA = np.sqrt(((tr[0] - br[0]) ** 2) + ((tr[1] - br[1]) ** 2))
    heightB = np.sqrt(((tl[0] - bl[0]) ** 2) + ((tl[1] - bl[1]) ** 2))

    # take the maximum of the width and height values to reach
    # our final dimensions
    maxWidth = max(int(widthA), int(widthB))
    maxHeight = max(int(heightA), int(heightB))
    return maxWidth, maxHeight


def warp_to_page(img):
    ''' Perspective warps an image to a page it finds within that image. '''
    preprocessed = prepare(img)
    max_approx, page_contour = find_largest_rectangle(preprocessed)

    if page_contour is None or max_approx is None:
        return None

    rect = get_points(max_approx)
    maxWidth, maxHeight = get_dimensions(rect)

    # construct our destination points which will be used to
    # map the screen to a top-down, "birds eye" view
    dst = np.array([
        [0, 0],
        [maxWidth - 1, 0],
        [maxWidth - 1, maxHeight - 1],
        [0, maxHeight - 1]], dtype="float32")

    # calculate the perspective transform matrix and warp
    # the perspective to grab the screen
    M = cv2.getPerspectiveTransform(rect, dst)
    warp = cv2.warpPerspective(img, M, (maxWidth, maxHeight))

    # The likeness of the found page to an expected page is calculated using
    # the ratio of the shortest side length to the longest side length. On
    # standard paper (A{n}) this ratio is to 1:sqrt(2), how close the ratio of
    # our side lengths is determines our confidence in the warp.
    ratio = max(maxWidth, maxHeight) / min(maxHeight, maxWidth)
    likeness = (math.sqrt(2) / ratio) * 100

    return likeness, warp
