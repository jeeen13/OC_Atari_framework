from .game_objects import GameObject
import sys
"""
RAM extraction for the game RIVER RAID. Supported modes: raw

Revised mode does not seem feasible for this game. The problem is that for the objects like Helicopter, FuelDepot etc.
only a relative x-Position is found in the RAM. How the exact position is calculated is unknown, it is possible that
the size of the objects (is stored in the RAM) somehow affects the x-Position.
Furthermore there was no y-Position for the Objects found in the RAM. It could be the case that their y-Position is like
the players y-Position not stored in the RAM.
"""

# MAX_NB_OBJECTS = {"Player": 1, "PlayerMissile": 1, "Bridge": 1, "Tanker": 6, "FuelDepot": 6,
#                   "Helicopter": 6, "Jet": 6}
MAX_NB_OBJECTS = {'PlayerScore': 6, 'Lives': 1}
MAX_NB_OBJECTS_HUD = {'PlayerScore': 6, 'Lives': 1}


def twos_comp(val):
    """compute the 2's complement of int value val in 4 bits"""
    if (val & (1 << 3)) != 0: # if sign bit is set e.g., 4bit: -8 -> 7
        val = val - (1 << 4)        # compute negative value
    return val      


class _DescendingObject(GameObject):
    _offset = None
    
    def __init__(self, xfr, x_off):
        super().__init__()
        self._xy = 15 * xfr - x_off, -5 -self.wh[1]
    
    def _update_xy(self, xfr, x_off, y_off): # xfr
        self._xy = 15 * xfr - x_off, self._xy[1] + y_off


class Player(GameObject):
    def __init__(self):
        self._xy = 77, 145
        self.wh = 7, 13
        self.rgb = 232, 232, 74
        self.hud = False


class PlayerMissile(GameObject):
    def __init__(self):
        self._xy = 0, 0
        self.wh = 1, 8
        self.rgb = 232, 232, 74
        self.hud = False


class Helicopter(_DescendingObject):
    _offset = 6
    fh = 10  # final height
    def __init__(self, xfr, x_off):
        super().__init__(xfr, x_off)
        self.wh = 8, 1
        self.rgb = 0, 64, 48
        self.hud = False
        self.xy = self.xy[0], self.xy[1] - self.wh[1]
    
    # def _update_xy(self, xfr, x_off, y_off): # xfr
    #     self._xy = 15 * xfr - x_off, self._xy[1] + y_off
    # def _update_xy(self, xfr, offset): # xfr
    #     self._xy = self._offset + 15 * xfr, self._xy[1] + 2 * offset


class Tanker(_DescendingObject):
    _offset = 12
    fh = 8
    def __init__(self, xfr, x_off):
        super().__init__(xfr, x_off)
        self.wh = 16, 1
        self.rgb = 84, 160, 197
        self.hud = False


class Jet(_DescendingObject):
    _offset = 12
    fh = 10
    def __init__(self, xfr, x_off):
        super().__init__(xfr, x_off)
        self.wh = 10, 1
        self.rgb = 117, 181, 239
        self.hud = False


class Bridge(_DescendingObject):
    _offset = 12
    def __init__(self, xfr, x_off):
        super().__init__(xfr, x_off)
        self.wh = 32, 18
        self.rgb = 134, 134, 29
        self.hud = False


class FuelDepot(_DescendingObject):
    _offset = 8
    fh = 24
    def __init__(self, xfr, x_off):
        super().__init__(xfr, x_off)
        self.wh = 7, 1
        self.rgb = 210, 91, 94
        self.hud = False
        self.xy = self.xy[0], self.xy[1] - self.wh[1]


class PlayerScore(GameObject):
    def __init__(self):
        self._xy = 97, 165
        self.rgb = 232, 232, 74
        self.wh = 6, 8
        self.hud = True

    def __eq__(self, o):
        return isinstance(o, PlayerScore) and self.xy == o.xy


class Lives(GameObject):
    def __init__(self):
        self._xy = 57, 192
        self.rgb = 232, 232, 74
        self.wh = 6, 8
        self.hud = True


_ram_to_class = [None, None, None, None, Jet, Helicopter, Helicopter, Tanker, Bridge, None, FuelDepot] # 9th would be houseandtree
global cntr, prev70, enemies


# parses MAX_NB* dicts, returns default init list of objects
def _get_max_objects(hud=False):

    def fromdict(max_obj_dict):
        objects = []
        mod = sys.modules[__name__]
        for k, v in max_obj_dict.items():
            for _ in range(0, v):
                objects.append(getattr(mod, k)())    
        return objects

    if hud:
        return fromdict(MAX_NB_OBJECTS_HUD)
    return fromdict(MAX_NB_OBJECTS)


def _init_objects_riverraid_ram(hud=False):
    """
    (Re)Initialize the objects
    """
    global cntr, prev70, enemies
    enemies = [None] * 6
    objects = [None] * 2 + enemies # Player, missile and 6 objects
    cntr, prev70 = 0, None
    if hud:
        objects.extend([PlayerScore(), Lives()])

    # objects.extend([Bridge(), Jet(), Helicopter(), Tanker(), FuelDepot()])
    return objects


def _detect_objects_riverraid_revised(objects, ram_state, hud=False):
    # player = objects[0]
    # if ram_state[70]:
    #     objects[0] = None
    # elif player is None:
    #     player = Player()
    #     objects[0] = player
    #     player.xy = ram_state[51] + 1, 145
    # else:
    #     player.xy = ram_state[51] + 1, 145

    # missile = objects[1]
    # # player missile
    # if ram_state[117] != 0 and 162 - ram_state[50] >= 0:  # else not firing
    #     if missile is None:
    #         missile = PlayerMissile()
    #         objects[1] = missile
    #     missile.xy = ram_state[117] - 1, 162 - ram_state[50]
    # elif missile is not None:
    #     objects[1] = None
    
    global cntr, prev70, enemies
    framskips = (cntr - ram_state[2]) % 256
    if ram_state[70] == 0 or ram_state[70] != prev70:
        speed = 1
    else: # hasn't fired yet
        speed = 0
    # print(framskips)
    # print(ram_state[70])
    # if prev70 == 0 and ram_state[70]:
    #     objects[2:8] = [None] * 6
    print(ram_state[11])
    for i in range(6):
        eobj = enemies[i]
        obj_type = ram_state[32 + i]
        obj_class = _ram_to_class[obj_type]
        x_off = twos_comp(ram_state[26 + i]//16) - 6
        # print(x_off)
        orientation = (ram_state[26 + i]%16)//8
        xanchor = ram_state[20+i]
        if obj_class is not None:
            if "Tanker" in str(obj_class) and i < 4:
                print("t:", i)
            # if not isinstance(eobj, obj_class):
            #     if i < 5 and isinstance(enemies[1+i], obj_class): # moving down
            #         eobj = enemies[1+i]
            #         enemies[1+i] = None
            #         eobj._update_xy(xanchor, x_off, 1)
            #     elif eobj is None:
            #         eobj = obj_class(xanchor, x_off)
            #     enemies[i] = eobj
            # else: # i == 5
            #     if eobj.y == 0 and eobj.h < eobj.fh:
            #         eobj.h += 1
            #         # print(f"update h {eobj}")
            #     elif eobj.y < 0 or eobj.h == eobj.fh:
            #         # print(f"update y {eobj}")
            #         eobj._update_xy(xanchor, x_off, 1)
            # if eobj.y + eobj.h >= 162:
            #     eobj.h = 162 - eobj.y
    for i, en in enumerate(enemies):
        if en is not None:
            if 0 <= en.y < 161:
                objects[2+i] = en
    # print(enemies, objects)
    # if hud:
    #     score, lives, _ = objects[9:12]
    #     score_value = riverraid_score(ram_state)
    #     if score_value >= 10:
    #         score.xy = 89, 165
    #         score.wh = 6, 8

    #     if score_value >= 100:
    #         score.xy = 81, 165
    #         score.wh = 6, 8

    #     if score_value >= 1000:
    #         score.xy = 73, 165
    #         score.wh = 6, 8

    #     if score_value >= 10000:
    #         score.xy = 65, 165
    #         score.wh = 6, 8
    cntr = ram_state[2]
    prev70 = ram_state[70]

    #     if score_value >= 100000:
    #         score.xy = 57, 165
    #         score.wh = 6, 8





def _detect_objects_riverraid_raw(info, ram_state):
    # for all the objects: the lowest RAM state so 20 for object position always references the object that is the next
    # object to leave the screen. So when a helicopter is passed and gets off the screen all other objects will move
    # one RAM position down.
    info["objects_pos"] = ram_state[20:26]  # only a relative position from 1 to 8. 1 equals to left side and 8 to the
    # right side. However there is an offset or something to move the objects a little bit
    info["object_size"] = ram_state[26:32] # size, orientation and offset
    info["object_type"] = ram_state[32:38]  # 10 = fuel depot, 6 = helicopter (normal), 7 = boat, 9 = house tree right,
    # 1, 2 and 3 = destroyed, 0 invisible, 8 = bridge, 4 = jet, 5 = helicopter
    info["grass_layout"] = ram_state[14:20]
    info["water_width"] = ram_state[38:44]  # 35 = normal, 12 = canal, 7 = spreads
    info["player_x"] = ram_state[51]  # start at x = 76, player_y is constant
    info["missile_x"] = ram_state[117]
    info["missile_y"] = ram_state[50]
    info["fuel_meter_high"] = ram_state[55]
    info["fuel_meter_low"] = ram_state[56]
    info["lives_"] = (ram_state[64] / 8) + 1
    info["score"] = riverraid_score(ram_state)
    info["fuel_meter"] = (ram_state[55] / 255) * 100


def riverraid_score(ram_state):
    """
    Returns the current score for River Raid. Each digit up to the hundreds of thousands position
    has its own RAM position. However in the RAM is the digit value times 8 represented f.e.
    ram value 24 represents a three on screen.

    Args:
        ram_state: current RAM representation of the game

    Returns:
        score (int): current score
    """
    score = 0
    # hundreds of thousands
    if ram_state[77] != 88:  # if the ram value is 88, the digit is not shown on the screen
        score = score + 100000 * ram_state[77] / 8
    # ten thousands
    if ram_state[79] != 88:
        score = score + 10000 * ram_state[79] / 8
    # thousands
    if ram_state[81] != 88:
        score = score + 1000 * ram_state[81] / 8
    # hundreds
    if ram_state[83] != 88:
        score = score + 100 * ram_state[83] / 8
    # tens
    if ram_state[85] != 88:
        score = score + 10 * ram_state[85] / 8
    # ones
    if ram_state[87] != 88:
        score = score + ram_state[87] / 8

    return score
