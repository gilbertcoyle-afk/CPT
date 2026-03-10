import math
import random as rand

def make_path(start_x, start_y, end_x, end_y):
    adj = end_x - start_x
    opp = end_y - start_y
    direction = math.atan2(adj, -opp)
    return direction

def find_path(max_x, max_y, min_x, min_y, no_go_x, no_go_y):
    x = range_gapped(min_x, max_x, (int(no_go_x) - 100), (int(no_go_x) + 100))
    y = range_gapped(min_y, max_y, (int(no_go_y) - 100), (int(no_go_y) + 100))
    return x,y

def range_gapped(start, end, gap_strt, gap_end):
    if gap_strt < start and gap_end > end:
        return rand.randint(start, end)
    if gap_strt < start:
        return rand.randint(gap_end, end)
    if gap_end > end:
        return rand.randint(start, gap_strt)
    else:
        range_1 = rand.randint(start, gap_strt)
        range_2 = rand.randint(gap_end, end)
    
    if rand.randint(1, 2) == 1:
        return range_1
    else:
        return range_2