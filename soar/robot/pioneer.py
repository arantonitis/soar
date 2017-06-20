from soar.geometry import *
from soar.robot.base import GenericRobot
from soar.geometry import Line
from soar.world.base import WorldObject

def clip(value, m1, m2):
    lower = min(m1, m2)
    upper = max(m1, m2)
    if value > upper:
        return upper
    elif value < lower:
        return lower
    else:
        return value

class PioneerRobot(GenericRobot, WorldObject):
    def __init__(self, io=None, pos=None):
        GenericRobot.__init__(self, io, pos)
        WorldObject.__init__(self, True, True)
        self.signals.update({'set_forward_velocity': self.set_forward_velocity,
                             'set_rotational_velocity': self.set_rotational_velocity,
                             'sonars': self.get_sonars})
        self.polygon = PointCollection([(-0.034120395949525435, -0.21988658579769327),
                                        (0.057113186972574566, -0.21988658579769327),
                                        (0.13931180489258044, -0.17002226170095702),
                                        (0.1961950134315429, -0.09869297431410165),
                                        (0.21649639551154948, -0.009746807794991423),
                                        (0.19619501343154294, 0.07919935872411882),
                                        (0.1393118048925805, 0.15052864611097416),
                                        (0.05711318697257454, 0.1901134142023067),
                                        (-0.03412039594952546, 0.1901134142023067),
                                        (-0.05163681302742546, 0.1901134142023067),
                                        (-0.051636813027425454, 0.15021341420230672),
                                        (-0.15323681302742542, 0.15021341420230672),
                                        (-0.22308681302742545, 0.07401341420230673),
                                        (-0.22308681302742545, -0.10378658579769329),
                                        (-0.15323681302742542, -0.17998658579769328),
                                        (-0.05163681302742544, -0.17998658579769328),
                                        (-0.051636813027425434, -0.21988658579769327)],
                                       None, fill='black', tags='pioneer')
        self.sonar_poses = [(0.013008094924083946, -0.20651169941255937, -1.57),
                            (0.09972419534513688, -0.18157953736419125, -1.21),
                            (0.16926510857462096, -0.12098273162239542, -0.6731984257692414),
                            (0.20785740388410556, -0.040845004669412655, -0.2243994752564138),
                            (0.20785740388410556, 0.04810116184969754, 0.2243994752564138),
                            (0.16926510857462107, 0.12823888880268036, 0.6731984257692414),
                            (0.09972419534513688, 0.18369591654177436, 1.21),
                            (0.013008094924083946, 0.20348830058744055, 1.57)]
        self.tags = 'pioneer'
        self.FV_CAP = 2.0  # TODO: These are not correct
        self.RV_CAP = 0.5
        self.SONAR_MAX = 1.5
        self.collided = False

    def set_forward_velocity(self, fv):
        if self.io is None:
            self.fv = clip(fv, -self.FV_CAP, self.FV_CAP)

    def set_rotational_velocity(self, rv):
        if self.io is None:
            self.rv = clip(rv, -self.RV_CAP, self.RV_CAP)

    def get_sonars(self):
        if self.io is None:
            sonars = [5.0]*8
            for i in range(len(self.sonar_poses)):
                # We take each sonar and build a line as long as the world's max dimension, and check for collisions
                temp = Pose(*self.sonar_poses[i])
                temp = temp.transform((self.polygon.center[0], self.polygon.center[1], -self.pos[2]))
                temp.rotate(self.polygon.center, self.pos[2])
                x0, y0 = temp[0], temp[1]
                x1, y1 = x0 + max(self.world.dimensions) * cos(temp[2]), y0 + max(self.world.dimensions) * sin(temp[2])
                ray = Line((x0, y0), (x1, y1))
                intersects = []
                for obj in self.world:
                    if obj is not self:
                        p = ray.collision(obj)
                        if p:
                            p = Point(*p)
                            intersects.append((p, p.distance(temp)))
                intersects.sort(key=lambda t: t[1])  # Find the nearest collision
                if len(intersects) > 0:
                    p, distance = intersects[0]
                    if distance < self.SONAR_MAX:
                        sonars[i] = distance
            return sonars

    def tick(self, duration):
        if not self.collided:
            GenericRobot.tick(self, duration)
            d_t = self.rv*duration
            self.polygon.rotate(self.polygon.center, d_t)
            for obj in self.world:
                if obj is not self:
                    if self.collision(obj):
                        self.collided = True
                        self.polygon.options['fill'] = 'red'

    def draw(self, canvas):
        self.polygon.recenter(self.pos)
        self.polygon.draw(canvas)
        sonars = self.get_sonars()
        for dist, pose in zip(sonars, self.sonar_poses):
            temp = Pose(*pose)
            temp = temp.transform((self.polygon.center[0], self.polygon.center[1], -self.pos[2]))
            temp.rotate(self.polygon.center, self.pos[2])
            if dist > 1.5:
                temp.draw(canvas, max(self.world.dimensions), tags=self.tags, fill='red')  # TODO: Change max dimensions
            else:
                temp.draw(canvas, dist, tags=self.tags, fill='gray')

    def collision(self, obj):
        if isinstance(obj, Line):
            lines = []
            for i in range(len(self.polygon)-1):
                p1, p2 = self.polygon[i], self.polygon[i+1]
                lines.append(Line(p1, p2))
            lines.append(Line(self.polygon[len(self.polygon)-1], self.polygon[0]))
            for line in lines:
                intersect = line.collision(obj)
                if intersect and line.has_point(intersect):
                    return intersect
            return None

    def delete(self, canvas):
        canvas.delete(self.tags)
