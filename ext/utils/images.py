"""Utility functions for drawing shapes and text on pixel-based images.

Provides helpers to manipulate raster pixel arrays, including drawing lines,
polygons, bounding boxes, and bitmap text using a simple 8-bit font system included in /utils/fonts.
Note that in blender, images raster have y=0 on the <u>bottom</u> of the image!

Classes:
    PixelCanvas: Checks out an image's pixel buffer once so multiple draw calls
        (e.g. several preview renderers drawing many labels in one frame) can share it
        instead of each re-reading/rewriting img.pixels individually. Pass a PixelCanvas
        instead of a raw Blender image to any draw_* function below to opt into this
        the function will draw into it without flushing, leaving the caller responsible
        for a single canvas.flush() at the end.

Functions:
    draw_color: Set or invert pixel color values.
    draw_line: Draw a line using Bresenham's algorithm.
    draw_polygon: Render polygon outlines and vertices.
    fill_polygon: Fill polygons using a scanline algorithm.
    draw_bitmap_text: Render text using a bitmap font.
    draw_bounding_box: Draw rectangular boxes on images.
    compute_text_pixel_width: Estimate text width in pixels.

Example:
    >>> from ext.utils.images import draw_line
    >>> pixels = list[...] # list of blender pixel objects
    >>> draw_line(pixels, (0, 0), (10, 10), (1, 1, 1, 1), 100, 100)
"""

from .fonts import EIGHT_BIT_BITMAP_FONT_HEIGHT, EIGHT_BIT_BITMAP_FONT
from typing import Tuple, Union, Optional, Any


def draw_color(pixel, color: Optional[Tuple[float, float, float, float]], index: int) -> None:
    """ Draws a pixel on the pixel canvas array of the given color at the given index.
    All fours channel are written.
    If the color is None, the pixel is instead inverted for maximum contrast.

    :param pixel: the pixel raster
    :param color: the color
    :param index: the index in the unwrapped pixel raster
    """
    if color:
        pixel[index]     = color[0]
        pixel[index + 1] = color[1]
        pixel[index + 2] = color[2]
        pixel[index + 3] = color[3]
    else:
        # Invert the pixel for visibility.
        pixel[index]     = 1 - pixel[index]
        pixel[index + 1] = 1 - pixel[index + 1]
        pixel[index + 2] = 1 - pixel[index + 2]
    return

def to_index(p: tuple, w: int, channels: int = 4) -> int:
    """ Computes the index in the unwrapped pixel raster of the given channels.

    :param p: point whose index is to be computed
    :param w: the width of the canvas
    :param channels: number of channels
    :return: the unwrapped index.
    """
    return (p[0] + p[1]*w)*channels


class PixelCanvas:
    """ Checks out a Blender image's pixel buffer once so that multiple draw calls (e.g. many
    renderers drawing many labels in a single preview frame) can share the same in-memory list or numpy array
    instead of each call re-reading img.pixels into a fresh list and writing/updating it back,
    which is very costly cost when drawing many small primitives (e.g. point clouds).

    Callers are responsible for calling flush() once after all drawing is done.
    """

    def __init__(self, img, channels: int = 4):
        self.img = img
        self.channels = channels
        self.width, self.height = img.size
        self.pixels = list(img.pixels)

    def index(self, p: tuple) -> int:
        return to_index(p, self.width, self.channels)

    def flush(self) -> None:
        """ Write the working buffer back to the Blender image and refresh it. """
        self.img.pixels[:] = self.pixels
        self.img.update()


def ensure_is_canvas(img_or_canvas: Union["PixelCanvas", Any], channels: int = 4) -> tuple["PixelCanvas", bool]:
    """ Resolve a PixelCanvas from either an existing canvas, which is reused as-is
    (the caller owns flushing it), or a raw Blender image, which is wrapped in a
    fresh canvas that this function's caller is then responsible for flushing
    immediately. This is not to break the previous version.

    :param img_or_canvas: a PixelCanvas or a raw Blender image object.
    :param channels: Number of color channels, used only when wrapping a raw image.
    :return: (canvas, owns_canvas) where owns_canvas is True if the caller must flush it.
    """
    if isinstance(img_or_canvas, PixelCanvas):
        return img_or_canvas, False
    return PixelCanvas(img_or_canvas, channels=channels), True


def draw_bounding_box(
        img, color: tuple[float, float, float, float],
        lower_point: Tuple[int, int], upper_point: Tuple[int, int], y_grows_up_to_down: bool = True,
        line_width: int = 1, channels: int = 4) -> None:
    """ Draw a bounding box on an image.

    Usages:
    POINTS =  (1000, 0, 1800, 50)
    POINTS_2 =  (1000, 50, 1800, 0)
    draw_bounding_box(img, COLOR, P0, P1, y_grows_up_to_down=True, line_width=5)
    draw_bounding_box(img, COLOR_2, P0_2, P1_2, y_grows_up_to_down=False, line_width=5)

    (613.1937172774869, 908.4112149532709, 1306.8062827225133, 191.77570093457945)
    compute_bounding_boxes
    The above commands have the same effect, so that the y_grows_up_to_down parameters allows to switch
    between cv2 repr into blender pixel repr where a higher pixel has a greater y.

    :param img: Blender image object
    :param color: RGBA color tuple
    :param lower_point: (x_min, y_min)
    :param upper_point: (x_max, y_max)
    :param y_grows_up_to_down: If True, y increases downward (image coords). If False, y increases upward (math coords).
    :param line_width: Thickness of box lines
    :param channels: Number of color channels (usually 4 for RGBA)
    """
    canvas, owns_canvas = ensure_is_canvas(img, channels)
    width, height = canvas.width, canvas.height
    pixels = canvas.pixels

    max_idx = to_index((width-1, height-1), width, channels=channels)

    def horizontal_line(point: tuple[int, int], line_length: int) -> None:
        nonlocal line_width, width
        for width_idx in range(line_width):
            idx0 = to_index( (point[0], point[1] + width_idx) , width, channels=channels)
            idx1 = to_index( (point[0] + line_length,  point[1] + width_idx) , width, channels=channels)
            for i in range(idx0, idx1 + 1*channels, channels):
                if i <= max_idx:
                    draw_color(pixels, color, i)

    def vertical_line(point: tuple[int, int], line_height: int) -> None:
        """Draw a vertical line starting at point, extending line_height pixels down"""
        for width_idx in range(line_width):
            start_x = point[0] + width_idx
            if start_x >= width:
                continue
            for y in range(point[1], point[1] + line_height):
                if y >= height:
                    continue
                idx = to_index((start_x, y), width, channels=channels)
                if idx <= max_idx:
                    draw_color(pixels, color, idx)

    # Handle coordinate system
    if y_grows_up_to_down:
        # Image coordinates: y increases downward
        p0 = lower_point
        p1 = upper_point
    else:
        # Math coordinates: y increases upward
        # Swap y coordinates
        p0 = (lower_point[0], upper_point[1])
        p1 = (upper_point[0], lower_point[1])

    box_width  = p1[0] - p0[0]
    box_height = p1[1] - p0[1]

    # Draw the two box horizontal lines
    horizontal_line((p0[0], p0[1]), box_width)
    horizontal_line((p0[0], p1[1]), box_width)

    # Draw the two box vertical lines
    vertical_line((p0[0], p0[1]), box_height)
    vertical_line((p1[0], p0[1]), box_height)

    if owns_canvas:
        canvas.flush()


def font_size_fit_box_perc(text: str, max_width: int, ratio: float = 1.0) -> int:
    """ Computes an estimate of the horizontal width so that a text occupies at most ratio% of the
    max_width provided. Note that we assume the width to be constant per character, so that this function
    may overshoot.

    :param text: The target text
    :param max_width: max reference width
    :param ratio: the ratio desired
    :return: estimate font size
    """
    # A generic reference size, assuming the text width is pretty much linear in the width.
    base_size = 3
    # this actually computes the real width, not the estimate: the estimate is the ratio below!
    base_width = compute_text_pixel_width(text, base_size)

    scale = max_width / base_width
    font_size = max(2, int(base_size * scale * ratio))
    return font_size

def compute_text_pixel_width(text: str, size: int) -> int:
    """ Computes the width for a given text with a given font size.

    :param text: the text
    :param size: the font size considered
    :return: the width in pixels.
    """
    width = 0
    for char in text:
        if char not in EIGHT_BIT_BITMAP_FONT:
            char = '_'
        char_bitmap = EIGHT_BIT_BITMAP_FONT[char]
        char_width_pixels = len(char_bitmap[0])
        width += char_width_pixels * size + min(2, 1 * size // 2)
    return width


def estimate_text_pixel_height(_text: str, size: int) -> int:
    """ Estimate the text height as the reference font height. Notice that the real
    height is a bit higher potentially due to letters exceeding the regular height (l, q, p, t...)

    We keep the _text as first argument for coherence with the other width estimation function.

    :param _text: the (unused) reference text, or ""
    :param size: the font size considered
    :return: estimated font height
    """
    return size*EIGHT_BIT_BITMAP_FONT_HEIGHT


def draw_bitmap_text(img, text: str, position: tuple[int, int] = (0, 0),
                     color: Optional[tuple[float, float, float, float]] = (1.0, 1.0, 1.0, 1.0),
                     size: int = 1,
                     channels: int = 4,
                     crop_width: int =None) -> None:
    """ Draws the given text over the image from a bitmap font from the given position,
    with the given color and with a given font size. The position is taken to be the upper-left
    angle of the text box. The font is an 8BIT font defined in utils/fonts.py

    :param crop_width: Crop the text after this width
    :param img: the pixel raster
    :param text: the text to write
    :param position: the upper left position
    :param color: the given color
    :param size: the size of the text, as multiples of the basic font size
    :param channels: the number of channels
    """

    canvas, owns_canvas = ensure_is_canvas(img, channels)
    width, height = canvas.width, canvas.height
    pixels = canvas.pixels

    x_offset, y_offset = position
    x_offset = int(x_offset)
    y_offset = int(y_offset)

    max_idx = to_index((width-1, height-1), width, channels=channels)

    current_x = x_offset

    for char_idx, char in enumerate(text):
        if char not in EIGHT_BIT_BITMAP_FONT:
            char = '_'

        # Extract the character
        char_bitmap = EIGHT_BIT_BITMAP_FONT[char]
        char_width_pixels = len(char_bitmap[0])

        for y, row in enumerate(char_bitmap):
            for x, pixel in enumerate(row):
                if pixel == '1':
                    # Scale up the character
                    for sy in range(size):
                        for sx in range(size):

                            pixel_x = current_x + x * size + sx
                            pixel_y = y_offset - y * size - sy
                            if not (0 <= pixel_x < width and 0 <= pixel_y < height):
                                continue
                            idx = int(to_index((pixel_x, pixel_y), width, channels=channels))
                            if idx <= max_idx:
                                draw_color(pixels, color,idx)

        current_x += char_width_pixels * size + min(2, 1*size // 2)

    if owns_canvas:
        canvas.flush()


def fill_polygon(img, polygon: list[tuple], color, channels: int = 4) -> None:
    """ Fills a given polygon on a raster of pixels with the given color.
    The polygon vertices have to be in clockwise direction. The scanline algorithm
    is used.

    :param channels: Number of channels
    :param img: the pixel raster
    :param polygon: a list of clockwise vertices
    :param color: the color of the polygon
    """
    canvas, owns_canvas = ensure_is_canvas(img, channels)
    width, height = canvas.width, canvas.height
    pixels = canvas.pixels

    # For each scanline
    min_y = min(p[1] for p in polygon)
    max_y = max(p[1] for p in polygon)

    for y in range(int(min_y), int(max_y) + 1):
        # Find intersections with polygon edges
        intersections = []

        for i in range(len(polygon)):
            p1 = polygon[i]
            p2 = polygon[(i + 1) % len(polygon)]

            # Check if edge crosses scanline y
            if (p1[1] <= y < p2[1]) or (p2[1] <= y < p1[1]):
                # Calculate x intersection
                if p2[1] != p1[1]:
                    x = p1[0] + (y - p1[1]) * (p2[0] - p1[0]) / (p2[1] - p1[1])
                    intersections.append(x)

        # Sort and fill between pairs
        intersections.sort()
        for i in range(0, len(intersections), 2):
            if i + 1 < len(intersections):
                x_start = int(intersections[i])
                x_end = int(intersections[i + 1])
                for x in range(x_start, x_end):
                    draw_color(pixels, color, to_index((x, y), width, channels=channels))

    if owns_canvas:
        canvas.flush()


def draw_thick_pixel(pixels, color, x: int, y: int, line_width: int, width:int, height: int, channels: int=4) -> None:
    """ Draws a "thick" pixel at the given point, drawing concentric squares to create a box of
    side line_width at the center point represented by (x,y).

    :param pixels: the pixels raster
    :param color: color of the pixels
    :param x: the x position
    :param y: the y position
    :param line_width: the line width
    :param width: the width of the canvas
    :param height: the height of the canvas
    :param channels: the number of channels
    """
    for l_dx in range(-line_width // 2, (line_width + 1) // 2):
        for l_dy in range(-line_width // 2, (line_width + 1) // 2):
            if 0 < x + l_dx < width and 0< y + l_dy < height:
                idx = to_index((x + l_dx, y + l_dy), width, channels=channels)
                draw_color(pixels, color, idx)


def draw_line(pixels: Union[list, Any], p0: tuple[int, int], p1: tuple[int, int],
              color: tuple[float, float, float, float], width, height,
              line_width: int = 1, channels: int = 4, ) -> None:
    """ Draw a line from p0 to p1 on an image using Bresenham's algorithm.
    NOTE that like all other functions in this module, the points are taken to be
    in the blender image convention, with the <u>bottom of the image having y==</u>

    :param height: The height of the canvas
    :param width: the width of the canvas
    :param pixels: the pixels list/blender object
    :param channels: the number of channels for each pixel
    :param p0: Starting point (x, y)
    :param p1: Ending point (x, y)
    :param color: RGBA color tuple (0.0 to 1.0)
    :param line_width: Line thickness in pixels
    """

    # Bresenham's line algorithm
    # https://github.com/encukou/bresenham/blob/master/bresenham.py
    x0, y0 = int(p0[0]), int(p0[1])
    x1, y1 = int(p1[0]), int(p1[1])

    # Safety checks
    if x0 == x1 and y0 == y1:
        # Single point
        draw_thick_pixel(pixels, color, x0, y0, line_width, width, height, channels)
        return

    dx = abs(x1 - x0)
    dy = abs(y1 - y0)
    sx = 1 if x1 > x0 else -1
    sy = 1 if y1 > y0 else -1
    err = dx - dy

    x, y = x0, y0

    # Prevent lock in from some strange error... who knows
    safety_idx = 0
    while safety_idx < max(2*width, 2*height):
        draw_thick_pixel(pixels, color, x, y, line_width, width, height, channels)

        if x == x1 and y == y1:
            break
        e2 = 2 * err
        if e2 > -dy:
            err -= dy
            x += sx
        if e2 < dx:
            err += dx
            y += sy

        safety_idx += 1


def draw_polygon(img, vertices: list[tuple[int, int]],
                 color: tuple[float, float, float, float],
                 line_width: int = 1, channels: int = 4, draw_wireframe:bool = True) -> None:
    """ Draw a polygon from a list of vertices on an image. The vertices are not assumed to be
    clockwise or counterclockwise, but they have to be ordered.

    :param draw_wireframe: Whether to draw separately the points as "wireframe" of the
        polygon
    :param img: Blender image object
    :param vertices: List of (x, y) tuples defining polygon vertices in order
    :param color: RGBA color tuple (0.0 to 1.0)
    :param line_width: Line thickness in pixels
    :param channels: Number of color channels (default 4 for RGBA)
    """
    if len(vertices) < 2:
        return

    canvas, owns_canvas = ensure_is_canvas(img, channels)
    width, height = canvas.width, canvas.height
    pixels = canvas.pixels
    # Draw lines between consecutive vertices, wrapping around to the first vertex.
    # NOTE that like all other such functions, it is assumed that the points follow blender convention
    # (e.g. the y=0 is at the bottom of the image)
    for i in range(len(vertices)):
        p0 = vertices[i]
        if draw_wireframe:
            draw_thick_pixel(pixels, color, p0[0], p0[1], line_width + 4, width, height, channels)

        p1 = vertices[(i + 1) % len(vertices)]  # Wraps to first vertex, if list has only one
        # point then this draws a point correctly (its handled inside draw_line)
        draw_line(pixels, p0, p1, color, width, height, line_width, channels)

    if owns_canvas:
        canvas.flush()