class RenderPlayer:
    __slots__ = ('pos', 'health', 'team', 'name', 'alive', 'bone_list', 'localplayer', 'weapon')
    def __init__(self, player):
        self.pos = player.pos
        self.health = player.health
        self.team = player.team
        self.name = player.name
        self.alive = player.alive
        self.bone_list = player.bone_list.copy()  # kopya
        self.localplayer = player.localplayer
        self.weapon = player.weapon

    def get_bounds(self, view_matrix, screen_size, w2s_func):
        # Aynı Player.get_bounds kodu
        origin = w2s_func(self.pos, view_matrix, screen_size)
        if not origin:
            return None
        top_pos = self.bone_list[6] if self.bone_list else (self.pos[0], self.pos[1], self.pos[2] + 65)
        top = w2s_func(top_pos, view_matrix, screen_size)
        if not top:
            return None
        height = origin[1] - top[1]
        width = height / 2.4
        x1 = top[0] - width / 2
        y1 = top[1] - width / 4
        x2 = origin[0] + width / 2
        y2 = origin[1]
        return (x1, y1), (x2, y2)

def world_to_screen(pos, view_matrix, screen_size):
    x = pos[0]
    y = pos[1]
    z = pos[2]

    m = view_matrix

    clip_x = m[0] * x + m[1] * y + m[2] * z + m[3]
    clip_y = m[4] * x + m[5] * y + m[6] * z + m[7]
    clip_w = m[12] * x + m[13] * y + m[14] * z + m[15]

    if clip_w < 0.1:
        return None

    ndc_x = clip_x / clip_w
    ndc_y = clip_y / clip_w

    screen_x = (screen_size[0] / 2) * (ndc_x + 1)
    screen_y = (screen_size[1] / 2) * (1 - ndc_y)

    return (screen_x, screen_y)


def distance(a, b):
    return ((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2 + (a[2] - b[2]) ** 2) ** 0.5
