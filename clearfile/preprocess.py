import cv2
import numpy as np

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
    new_image = img.copy()
    mask = np.full(img.shape, (0, 0, 0), dtype=img.dtype)
    preprocessed = prepare(img)
    page_contour = find_largest_rectangle(preprocessed)
    if page_contour is not None:
        cv2.fillPoly(mask, [page_contour], (255, 255, 255))
        mask = np.logical_not(mask)
        new_image[mask] = 255
        return crop(new_image, page_contour)
    else:
        return None


def conv_to_bw(img):
    ''' Convert an image to black and white using thresholding. '''
    img_gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    _, img_bw = cv2.threshold(img_gray, 128, 255, cv2.THRESH_BINARY_INV)
    return img_bw


def deskew(img):
    ''' Deskew image content with respect to the background of the image. '''
    # Take all points that aren't black
    coords = np.column_stack(np.where(img > 0))
    # Find the minimum area rectangle that encompasses all of those points
    # We only care about the angle of this rectangle, because we're going to
    # rotate it.
    angle = cv2.minAreaRect(coords)[-1]

    # The angle given by minAreaRect is in the range [-90, 0), so we need to
    # convert it to a positive angle to correct by.
    if angle < -45:
        # A special case exists where the angle is -45 degrees, we have to add
        # 90 degrees to the angle
        angle = -(90 + angle)
    else:
        angle = -angle

    h, w = img.shape[:2]
    center = (w // 2, h // 2)

    rotation_matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
    rotated = cv2.warpAffine(img, rotation_matrix, (w, h),
                             flags=cv2.INTER_CUBIC,
                             borderMode=cv2.BORDER_REPLICATE)
    return rotated
