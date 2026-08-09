"""Records what icons.py draws as SVG instead of as pixels.

The icons are the one thing the cover image and the site have to agree on down to the
stroke: on the PNG they are drawn by PIL, on the site they are vectors that stay sharp
at any zoom. Instead of keeping a second, hand-written set of SVG icons in step with
icons.py, this module hands the icon functions something that behaves like an
ImageDraw and writes down what they asked for.

Only the four calls icons.py actually makes are implemented. Anything else raises —
a silently dropped call would surface as a missing detail in one of ten small drawings
that nobody looks at twice.

Two places where SVG does not mean what PIL means, both measured rather than guessed:

- PIL draws the outline of an ellipse *inside* the bounding box, SVG centres the stroke
  on the path. So a stroked ellipse gets its radii pulled in by half the stroke width,
  and fill and stroke become two elements.
- The angles of PIL's arc are parametric, not geometric: the point at angle a is
  (cx + rx·cos a, cy + ry·sin a), which is exactly what an SVG arc command wants.
"""
import math


def num(v):
    """Short decimal — the markup ends up inline in every collection page."""
    s = '%.2f' % v
    return s.rstrip('0').rstrip('.') if '.' in s else s


def col(rgb):
    return '#%02x%02x%02x' % (rgb[0], rgb[1], rgb[2])


def attrs(**kw):
    return ''.join(' %s="%s"' % (k.replace('_', '-'), v) for k, v in kw.items() if v is not None)


class SvgRecorder:
    """Quacks like ImageDraw.Draw, collects SVG elements."""

    def __init__(self):
        self.parts = []

    # -- the four calls icons.py makes ------------------------------------
    def polygon(self, xy, fill=None, outline=None, width=1):
        pts = ' '.join('%s,%s' % (num(x), num(y)) for x, y in xy)
        self.parts.append('<polygon points="%s"%s/>' % (pts, attrs(
            fill=col(fill) if fill else 'none',
            stroke=col(outline) if outline else None,
            stroke_width=num(width) if outline else None,
            stroke_linejoin='round' if outline else None)))

    def line(self, xy, fill=None, width=0, joint=None):
        if fill is None or width < 1:
            return                                # PIL draws nothing either
        pts = ' '.join('%s,%s' % (num(x), num(y)) for x, y in xy)
        # PIL's thick line has flat ends; with joint='curve' it rounds the corners, and
        # round corners are the better reading of the notches it leaves without.
        self.parts.append('<polyline points="%s" fill="none"%s/>' % (pts, attrs(
            stroke=col(fill), stroke_width=num(width),
            stroke_linejoin='round', stroke_linecap='butt')))

    def ellipse(self, xy, fill=None, outline=None, width=1):
        (x0, y0), (x1, y1) = self._pair(xy)
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        rx, ry = (x1 - x0) / 2, (y1 - y0) / 2
        if fill:
            self.parts.append('<ellipse%s/>' % attrs(
                cx=num(cx), cy=num(cy), rx=num(rx), ry=num(ry), fill=col(fill)))
        if outline and width >= 1:
            # the stroke sits inside the box in PIL, on the path in SVG
            ix, iy = max(rx - width / 2, 0.01), max(ry - width / 2, 0.01)
            self.parts.append('<ellipse fill="none"%s/>' % attrs(
                cx=num(cx), cy=num(cy), rx=num(ix), ry=num(iy),
                stroke=col(outline), stroke_width=num(width)))

    def arc(self, xy, start, end, fill=None, width=1):
        if fill is None or width < 1:
            return
        (x0, y0), (x1, y1) = self._pair(xy)
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        # like ellipse, PIL lays the band inside the box — measured, not assumed
        rx = max((x1 - x0) / 2 - width / 2, 0.01)
        ry = max((y1 - y0) / 2 - width / 2, 0.01)
        sweep = (end - start) % 360 or 360
        if sweep >= 360:                          # SVG cannot draw a full turn in one arc
            mid = start + 180
            self.arc([x0, y0, x1, y1], start, mid, fill, width)
            self.arc([x0, y0, x1, y1], mid, start, fill, width)
            return

        def at(a):
            r = math.radians(a)
            return cx + rx * math.cos(r), cy + ry * math.sin(r)

        sx, sy = at(start); ex, ey = at(end)
        # sweep-flag 1: PIL's growing angle and SVG's positive sweep both turn clockwise
        # on a screen whose y points down. The ends are cut off square, as PIL cuts them.
        self.parts.append('<path d="M %s %s A %s %s 0 %d 1 %s %s" fill="none"%s/>' % (
            num(sx), num(sy), num(rx), num(ry), 1 if sweep > 180 else 0, num(ex), num(ey),
            attrs(stroke=col(fill), stroke_width=num(width), stroke_linecap='butt')))

    # -- anything else is a gap, not a detail to skip ---------------------
    def __getattr__(self, name):
        raise NotImplementedError(
            "svgdraw cannot record %r — icons.py grew a new drawing call, teach it here" % name)

    @staticmethod
    def _pair(xy):
        """PIL takes a bounding box either as four numbers or as two corners."""
        if len(xy) == 4 and not hasattr(xy[0], '__len__'):
            return (xy[0], xy[1]), (xy[2], xy[3])
        return tuple(xy[0]), tuple(xy[1])

    def markup(self):
        return ''.join(self.parts)


def record(fn, s):
    """One icon of icons.py at radius scale `s`, centred on the origin, as SVG markup.

    Callers pass the same `s` the renderer passes (`size * S`), because the stroke widths
    inside icons.py are clamped with `max(2, int(s * k))` — recorded at any other scale
    those clamps resolve differently and the vector icon drifts away from the drawn one.
    The markup is placed with a matching `scale(1/S)`.
    """
    rec = SvgRecorder()
    fn(rec, 0.0, 0.0, s)
    return rec.markup()
