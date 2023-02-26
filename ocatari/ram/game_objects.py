class GameObject:
    GET_COLOR = False
    GET_WH = False

    def __init__(self):
        self.rgb = (0, 0, 0)
        self._xy = (0, 0)
        self.wh = (0, 0)
        self._prev_xy = (0, 0)
        self.hud = False
        self.visible = True

    def __repr__(self):
        return f"{self.__class__.__name__} at ({self._xy[0]}, {self._xy[1]})"

    @property
    def category(self):
        return self.__class__.__name__

    @property
    def xy(self):
        return self._xy

    @xy.setter
    def xy(self, xy):
        self._prev_xy = self._xy
        self._xy = xy

    # returns 2 lists with current and past coords
    @property
    def h_coords(self):
        """
        history of coordinates
        """
        return [self._xy, self._prev_xy]

    @property
    def dx(self):
        return self._xy[0] - self._prev_xy[0]

    @property
    def dy(self):
        return self._xy[1] - self._prev_xy[1]

    @property
    def xywh(self):
        return self._xy[0], self._xy[1], self.wh[0], self.wh[1]

    @property
    def x(self):
        return self._xy[0]

    @property
    def y(self):
        return self._xy[1]

    @property
    def w(self):
        return self.wh[0]

    @w.setter
    def w(self, w):
        self.wh = w, self.h

    @property
    def h(self):
        return self.wh[1]

    def is_on_top(self, other):
        return (other.x <= self.x <= other.x + other.w) and \
            (other.y <= self.y <= other.y + other.h) 