"""


"""
from typing import List, Union


def convert_camera_centered_to_absolute_pixels_0y_top_invert(
        ximn_ymin_xmax_ymax: tuple[float, float, float, float], width: int, height: int
) -> tuple[int, int, int, int]:
    """ The resulting values are given so that the y values GROW as the point goes
    DOWN on the picture, e.g. the y value is 0 AT THE TOP.
    This is unlike blender image pixel system, where y value decreases as the point goes
    DOWN on the picture.

    :param ximn_ymin_xmax_ymax:
    :param width:
    :param height:
    :return:
    """
    # Unpack the values
    x_min, y_min, x_max, y_max = ximn_ymin_xmax_ymax

    x_min_px = int((x_min + 1) * width / 2)
    x_max_px = int((x_max + 1) * width / 2)
    y_min_px = int((y_max + 1) * height / 2)
    y_max_px = int((y_min + 1) * height / 2)

    return x_min_px, y_min_px, x_max_px, y_max_px

def convert_camera_centered_to_absolute_pixels_0y_top(
        ximn_ymin_xmax_ymax: tuple[float, float, float, float], width: int, height: int
) -> tuple[int, int, int, int]:
    """ The resulting values are given so that the y values GROW as the point goes
    DOWN on the picture, e.g. the y value is 0 AT THE TOP.
    This is unlike blender image pixel system, where y value decreases as the point goes
    DOWN on the picture.

    :param ximn_ymin_xmax_ymax:
    :param width:
    :param height:
    :return:
    """
    # Unpack the values
    x_min, y_min, x_max, y_max = ximn_ymin_xmax_ymax

    x_min_px = int((x_min + 1) * width / 2)
    x_max_px = int((x_max + 1) * width / 2)
    y_min_px = int((y_min + 1) * height / 2)
    y_max_px = int((y_max + 1) * height / 2)

    return x_min_px, y_min_px, x_max_px, y_max_px

def convert_camera_centered_to_absolute_pixels_y_inverted(
    ximn_ymin_xmax_ymax: tuple[float, float, float, float], width: int, height: int
) -> tuple[int, int, int, int]:
    """

    :param ximn_ymin_xmax_ymax:
    :param width:
    :param height:
    :return:
    """
    x_min, y_min, x_max, y_max = convert_camera_centered_to_absolute_pixels_0y_top(ximn_ymin_xmax_ymax, width, height)
    y_min = height - y_min
    y_max = height - y_max
    return x_min, y_min, x_max, y_max


def convert_camera_centered_to_absolute_pixels(
    ximn_ymin_xmax_ymax: tuple[float, float, float, float], width: int, height: int
) -> tuple[int, int, int, int]:
    """

    :param ximn_ymin_xmax_ymax:
    :param width:
    :param height:
    :return:
    """
    x_min, y_min, x_max, y_max = convert_camera_centered_to_absolute_pixels_0y_top(ximn_ymin_xmax_ymax, width, height)
    return x_min, y_min, x_max, y_max

def convert_camera_centered_to_top_left_0_1(
    ximn_ymin_xmax_ymax: tuple[float, float, float, float]
):
    """

    :param ximn_ymin_xmax_ymax:
    :return:
    """
    x_min = (ximn_ymin_xmax_ymax[0] + 1) / 2
    y_min = (ximn_ymin_xmax_ymax[1] + 1) / 2
    x_max = (ximn_ymin_xmax_ymax[2] + 1) / 2
    y_max = (ximn_ymin_xmax_ymax[3] + 1) / 2
    return x_min, y_min, x_max, y_max

def convert_camera_centered_to_yolo(
    ximn_ymin_xmax_ymax: tuple[float, float, float, float]
):
    """ Convert image-centered [-1, 1] bbox to YOLO [0, 1]

    :param ximn_ymin_xmax_ymax: the camera-centered [-1, 1] bbox
    :return: 4 numbers in YOLO format x_center, y_center and sizes.
    """
    x_min, y_min, x_max, y_max = ximn_ymin_xmax_ymax
    x_center = ((x_min + x_max) / 2 + 1) / 2
    y_center = ((y_min + y_max) / 2 + 1) / 2
    width = abs(x_max - x_min) / 2
    height = abs(y_max - y_min) / 2
    return x_center, y_center, width, height


def convert_camera_centered_to_coco(
    ximn_ymin_xmax_ymax: tuple[float, float, float, float],
    width: int,
    height: int
) -> tuple[float, float, float, float]:
    """ Convert image-centered [-1, 1] bbox to COCO [x, y, width, height] in pixels.

    COCO format: [x, y, width, height] where x,y is top-left corner in pixels.

    :param ximn_ymin_xmax_ymax: the camera-centered [-1, 1] bbox
    :param width: width of the frame
    :param height: height of the frame
    :return: 4 numbers in COCO format [x_pixel, y_pixel, width_pixel, height_pixel]
    """
    x_min, y_min, x_max, y_max = ximn_ymin_xmax_ymax

    # Convert from [-1, 1] to [0, 1]. the -1..1 range is used initially with
    # frustum-center coordinates. this converts to left-upper corner coordinates
    x_min_norm = (x_min + 1) / 2
    x_max_norm = (x_max + 1) / 2
    y_min_norm = (y_min + 1) / 2
    y_max_norm = (y_max + 1) / 2

    # Convert from [0, 1] to pixel coordinates
    x_pixel = x_min_norm * width
    y_pixel = y_min_norm * height
    width_pixel = abs(x_max_norm - x_min_norm) * width
    height_pixel = abs(y_max_norm - y_min_norm) * height

    return x_pixel, y_pixel, width_pixel, height_pixel


def convert_camera_centered_to_pascal_voc(
    bbox_camera_centered: tuple[float, float, float, float],
    width: int,
    height: int
) -> tuple[int, int, int, int]:
    """
    Convert camera-centered [-1, 1] bounding box to Pascal VOC format.

    Pascal VOC format: [xmin, ymin, xmax, ymax] in pixel coordinates (integers)
    where (xmin, ymin) is top-left corner and (xmax, ymax) is bottom-right corner.

    Camera-centered format: [x_min, y_min, x_max, y_max] in [-1, 1] range,
    where center of image is (0, 0).

    :param bbox_camera_centered: Tuple of (x_min, y_min, x_max, y_max) in [-1, 1]
    :param width: width of the frame
    :param height: height of the frame
    :return: Tuple of (xmin, ymin, xmax, ymax) in pixel coordinates
    """
    x_min, y_min, x_max, y_max = bbox_camera_centered

    # Convert from [-1, 1] to [0, 1]
    x_min_norm = (x_min + 1) / 2
    x_max_norm = (x_max + 1) / 2
    y_min_norm = (y_min + 1) / 2
    y_max_norm = (y_max + 1) / 2

    # Convert from [0, 1] to pixel coordinates
    xmin_pixel = x_min_norm * width
    xmax_pixel = x_max_norm * width
    ymin_pixel = y_min_norm * height
    ymax_pixel = y_max_norm * height

    # Ensure xmin < xmax and ymin < ymax
    xmin = int(min(xmin_pixel, xmax_pixel))
    xmax = int(max(xmin_pixel, xmax_pixel))
    ymin = int(min(ymin_pixel, ymax_pixel))
    ymax = int(max(ymin_pixel, ymax_pixel))

    # Clamp to image bounds
    xmin = max(0, min(xmin, width - 1))
    xmax = max(1, min(xmax, width))
    ymin = max(0, min(ymin, height - 1))
    ymax = max(1, min(ymax, height))

    return xmin, ymin, xmax, ymax


def convert_camera_point_list_absolute_pixels_y_inverted(
    p_list: List[tuple[float, float]], width: int, height: int
) -> list[tuple[int, int]]:
    """

    :param p_list:
    :param width:
    :param height:
    :return:
    """
    pixel_list = list()
    for p in p_list:
        x_p = int((p[0] + 1) * width / 2)
        y_p = height-int((p[1] + 1) * height / 2)
        pixel_list.append((x_p, y_p))
    return pixel_list

def convert_camera_point_list_absolute_pixels_y(
    p_list: List[tuple[float, float]], width: int, height: int
) -> list[tuple[int, int]]:
    """

    :param p_list:
    :param width:
    :param height:
    :return:
    """
    pixel_list = list()
    for p in p_list:
        x_p = int((p[0] + 1) * width / 2)
        y_p = int((p[1] + 1) * height / 2)
        pixel_list.append((x_p, y_p))
    return pixel_list



# ------ General geometry conversion ------

Geometry = Union[ tuple[float, float, float, float], List[tuple[float, float]], dict]


def convert_geometry_camera_to_absolute_y_inverted(
    geometry: Geometry,  # flexible structure
    width: int, height: int
) -> Geometry:
    """ """

    if isinstance(geometry, tuple):
        return convert_camera_centered_to_absolute_pixels_y_inverted(geometry, width, height)
    if isinstance(geometry, list):
        # polygonal data
        return convert_camera_point_list_absolute_pixels_y_inverted(geometry, width, height)
    else:
        raise NotImplementedError(f"Conversion with geometry type f{type(geometry)} not supported")
