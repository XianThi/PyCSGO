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
