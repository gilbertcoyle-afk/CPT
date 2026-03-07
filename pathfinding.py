import math
import random as rand

def make_path(start_x, start_y, end_x, end_y):
    global transfer
    adj = end_x - start_x
    opp = end_y - start_y
    direction = math.atan(opp/adj)
    return direction

def find_path(max_x, max_y, min_x, min_y, no_go_x, no_go_y):
    x = rand.randint(min_x, max_x)
    while x in range(int(no_go_x) - 20, int(no_go_x) +20):
        x = rand.randint(min_x, max_x)
    y = rand.randint(min_y, max_y)
    while y in range(int(no_go_y) - 20, int(no_go_y) +20):
        x = rand.randint(min_y, max_y)
    return [x,y]