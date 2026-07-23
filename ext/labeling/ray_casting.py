"""


[ References ]
https://github.com/DLR-RM/BlenderProc/blob/main/blenderproc/python/camera/CameraValidation.py
https://blender.stackexchange.com/questions/269014/list-all-occluded-objects-from-camera

"""

try:
    from numpy import linspace
except ImportError:
    def linspace(start, stop, num):
        """Simple fallback for np.linspace, using a generator expression to avoid
        constructing a useless large array."""
        step = (stop - start) / (num - 1) if num > 1 else 0
        return (start + step * i for i in range(num))

from collections import defaultdict
from math import sqrt, degrees, atan2
from mathutils import Vector
from itertools import chain
from typing import Any, Set, Dict, Tuple, List, Union, Iterable, Callable
from dataclasses import dataclass

import bpy

@dataclass
class Point:

    x: float
    y: float


@dataclass
class BoundingBox:

    min_x: float
    min_y: float
    max_x: float
    max_y: float

@dataclass
class PolygonConvexHull:

    vertices: Iterable[Point]


def get_visible_objects_from_camera(scene, depsgraph,
        camera,
        resolution_x: int = 4, resolution_y: int = 4,
        num_ray: int = 0,
        compute_mapping: bool = False,
        compute_dist: bool = False,
        compute_normal: bool = False
    ) -> Union[Set[Any], Dict[Any, List]]:
    """

    :param scene:
    :param depsgraph:
    :param camera:
    :param resolution_x:
    :param resolution_y:
    :param num_ray:
    :param compute_mapping:
    :param compute_dist:
    :param compute_normal:
    :return:
    """
    # Get vectors which define view frustum of camera
    top_right, _, bottom_left, top_left = camera.data.view_frame(scene=scene)

    camera_quaternion = camera.matrix_world.to_quaternion()
    camera_translation = camera.matrix_world.translation

    if num_ray:
        # We know that the numbers of ray shot is len(x_range)*len(y_range) so we must have
        # assuming resolution_x = resolution_y
        # ( top_right[0]-top_left[0] / resolution_x ) * (bottom_left[1]-top_left[1]) / resolution_x) = num_rays
        # hence we have
        resolution_x = resolution_y = min(30, int(sqrt(
            (top_right[0] - top_left[0]) * (bottom_left[1] - top_left[1]) / num_ray)))

    # Get iteration range for both the x and y axes, sampled based on the resolution
    x_range = linspace(top_left[0], top_right[0], resolution_x)
    y_range = linspace(top_left[1], bottom_left[1], resolution_y)

    z_dir = top_left[2]

    hit_data = set()
    bounding_boxes_mappings: Dict[Any, List] = defaultdict(list)
    # iterate over all X/Y coordinates
    for x in x_range:
        for y in y_range:
            # get current pixel vector from camera center to pixel
            pixel_vector = Vector((x, y, z_dir))
            # rotate that vector according to camera rotation
            pixel_vector.rotate(camera_quaternion)
            pixel_vector.normalize()

            is_hit, location, normal, _, hit_obj, _ = scene.ray_cast(depsgraph, camera_translation, pixel_vector)

            if not is_hit:
                continue
            hit_data.add(hit_obj)
            # Keep track of all hits
            if compute_mapping:

                init_tup: tuple = ()
                # Compute normal if required
                if compute_normal:
                    init_tup += normal,
                # Compute distance if required
                if compute_dist:
                    distance = (location - camera_translation).length
                    init_tup += distance,

                x_normalized = (x - top_left[0]) / (top_right[0] - top_left[0]) * 2 - 1
                y_normalized = (y - top_left[1]) / (bottom_left[1] - top_left[1]) * 2 - 1

                # Just keep track of tuples, do not burden API user with a list with 1 item.
                if not compute_normal and not compute_dist:
                    bounding_boxes_mappings[hit_obj].append((x_normalized, y_normalized))
                else:
                    bounding_boxes_mappings[hit_obj].append( init_tup + ((x_normalized, y_normalized),) )


    if not compute_mapping:
        return hit_data
    else: return bounding_boxes_mappings


def get_minimal_bounding_box_fast(points: List[Tuple]):
    """

    :param points:
    :return:
    """
    if not points:
        return None
    x_min = x_max = points[0][0]
    y_min = y_max = points[0][1]

    for p in points[1:]:
        x = p[0]
        y = p[1]
        if x < x_min:
            x_min = x
        elif x > x_max:
            x_max = x

        if y < y_min:
            y_min = y
        elif y > y_max:
            y_max = y

    return x_min, y_min, x_max, y_max


def normalized_center_coordinate_to_pixel(x, y, width, height):
    pixel_x = (x + 1) * width / 2
    pixel_y = (1 - y) * height / 2  # The (1 - y) flips
    return pixel_x, pixel_y


def estimate_visibility_3d(obj, camera, depsgraph, context, render, visible_geometry,
                           area_func: Callable):
    """Compare 3D bbox projected area vs actual visible bbox"""


    camera_bbox = compute_object_camera_space_projected_bbox(obj, depsgraph, camera, context, render)

    bbox_3d_area = compute_bbox_area(camera_bbox)
    # Compute the actually visible area
    bbox_visible_area = float(area_func(visible_geometry))

    occlusion = bbox_visible_area / bbox_3d_area if bbox_3d_area > 0 else 1.0
    return occlusion, camera_bbox

def compute_camera_space_boxes(objects: Iterable[Any], camera, depsgraph, context, render) \
        -> Dict[Any, Tuple[float, float, float, float]]:
    """

    :param objects:
    :param camera:
    :param depsgraph:
    :param context:
    :param render:
    :return:
    """
    return { obj: compute_object_camera_space_projected_bbox(obj, depsgraph, camera, context, render)
             for obj in objects }


def compute_area_ratio(xyxy1, xyxy2, area_func_1: Callable, area_func_2: Callable) -> float:
    """

    :param area_func_2:
    :param area_func_1:
    :param xyxy1:
    :param xyxy2:
    :return:
    """
    area_1 = area_func_1(xyxy1)
    area_2 = area_func_2(xyxy2)
    if abs(area_2) < 1e-4:
        return 0.0
    return area_1 / area_2


def union_bounding_boxes(bounding_boxes: Iterable[tuple[float, float, float, float]]) -> tuple[float, float, float, float]:
    """

    :param bounding_boxes:
    :return:
    """
    min_x = float(min(bb[0] for bb in bounding_boxes))
    max_x = float(max(bb[2] for bb in bounding_boxes))
    min_y = float(min(bb[1] for bb in bounding_boxes))
    max_y = float(max(bb[3] for bb in bounding_boxes))

    return min_x, min_y, max_x, max_y

def compute_object_camera_space_projected_bbox(obj, depsgraph, camera, context, render) -> tuple[float, float, float, float]:
    """

    :param depsgraph:
    :param obj:
    :param camera:
    :param context:
    :param render:
    :return:
    """

    obj_eval = obj.evaluated_get(depsgraph)
    points = list()
    bounding_box = obj_eval.bound_box
    for threed_p in bounding_box:
        local_point = Vector((threed_p[0], threed_p[1], threed_p[2]))
        transform = obj_eval.matrix_world
        point = transform @ local_point
        proj = project_3d_point(camera, point, context, render)
        points.append(proj)

    min_x = float(min(p[0] for p in points))
    max_x = float(max(p[0] for p in points))
    min_y = float(min(p[1] for p in points))
    max_y = float(max(p[1] for p in points))

    return min_x, min_y, max_x, max_y


def compute_bbox_area(bbox):
    """Compute area from (x_min, y_min, x_max, y_max)"""
    x_min, y_min, x_max, y_max = bbox
    return abs(x_max - x_min) * abs(y_max - y_min)


def project_3d_point(camera: bpy.types.Object,
                     p: Vector,
                     context,
                     render) -> Vector:

    # https://blender.stackexchange.com/questions/16472/how-can-i-get-the-cameras-projection-matrix
    """
    Given a camera and its projection matrix M;
    given p, a 3d point to project:

    Compute P’ = M * P
    P’= (x’, y’, z’, w')

    Ignore z'
    Normalize in:
    x’’ = x’ / w’
    y’’ = y’ / w’

    x’’ is the screen coordinate in normalised range -1 (left) +1 (right)
    y’’ is the screen coordinate in  normalised range -1 (bottom) +1 (top)

    :param context:
    :param camera: The camera for which we want the projection
    :param p: The 3D point to project
    :param render: The render settings associated to the scene.
    :return: The 2D projected point in normalized range [-1, 1] (left to right, bottom to top)
    """

    # Get the two components to calculate M
    modelview_matrix = camera.matrix_world.inverted()
    projection_matrix = camera.calc_matrix_camera(
        context.evaluated_depsgraph_get(),
        x = render.resolution_x,
        y = render.resolution_y,
        scale_x = render.pixel_aspect_x,
        scale_y = render.pixel_aspect_y,
    )

    # print(projection_matrix * modelview_matrix)
    # Compute P’ = M * P
    p1 = projection_matrix @ modelview_matrix @ Vector((p[0], p[1], p[2], 1))

    # Normalize in: x’’ = x’ / w’, y’’ = y’ / w’
    p2 = Vector((p1.x / p1.w, p1.y / p1.w))

    return p2


def compute_polygon_area(vertices: list[tuple[float, float]]) -> float:
    """ Compute polygon area using the Shoelace formula.

    Works for any simple polygon (convex or concave).
    Vertices should be in order (clockwise or counterclockwise). Other functions
    in the code base use a clockwise convention.

    :param vertices:
    :return:
    """
    if len(vertices) < 3:
        return 0.0

    area = 0.0
    n = len(vertices)

    for i in range(n):
        x1, y1 = vertices[i]
        x2, y2 = vertices[(i + 1) % n]  # Next vertex (wraps around)
        area += x1 * y2 - x2 * y1

    return abs(area) / 2.0



def simplify_by_angle(points, min_angle=10.0):
    """Remove points where the angle change is small"""

    if len(points) < 3:
        return points

    def angle_between(p1, p2, p3):
        """Calculate angle at p2"""
        x1, y1 = p1
        x2, y2 = p2
        x3, y3 = p3

        v1 = (x1 - x2, y1 - y2)
        v2 = (x3 - x2, y3 - y2)

        dot = v1[0] * v2[0] + v1[1] * v2[1]
        det = v1[0] * v2[1] - v1[1] * v2[0]
        ang = abs(degrees(atan2(det, dot)))

        return min(ang, 180 - ang)

    simplified = [points[0]]
    for i in range(1, len(points) - 1):
        angle = angle_between(points[i - 1], points[i], points[i + 1])
        if angle > min_angle:
            simplified.append(points[i])
    simplified.append(points[-1])

    return simplified


def cross(o, a, b):
    return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

def compute_convex_hull(point_cloud: Union[ List[Tuple[int, int]], List[List]], merge: bool = False):
    """Graham scan algorithm for convex hull"""

    if merge:
        # multiple
        points = sorted(set(chain.from_iterable(point_cloud)))
    else:
        points = sorted(set(point_cloud))
    if len(points) <= 1:
        return points

    # Build lower hull
    lower = []
    for p in points:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)

    # Build upper hull
    upper = []
    for p in reversed(points):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)

    return lower[:-1] + upper[:-1]


Geometry = Union[ tuple[int, int, int, int], List[tuple[int, int]], dict]


def geometry_bounds(geometry: Geometry) -> tuple:
    """

    :param geometry:
    :return:
    """
    if isinstance(geometry, tuple):
        # For a bbox geometry, the bounds are given by the geometry itself
        return geometry
    elif isinstance(geometry, list):
        return get_minimal_bounding_box_fast(geometry)
    else:
        raise TypeError("geometry type not yet implemented for geometry bounds")

def compute_geometry_area(geometry: Geometry) -> float:
    pass
