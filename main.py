#all assests are from the Legacy Console Edition of Minecraft source code leak

import pygame as pg
import math
import pathfinding


pg.init()
pg.key.set_repeat(5, 5)
turning_right = False
moving_back = False
moving_forward = False
turning_left = False
scrn_h = 1000
scrn_w = 1000
clock = pg.time.Clock()
running = True
screen = pg.display.set_mode((scrn_w, scrn_h))
criminal = pg.image.load("MapIcon_0.png").convert_alpha()
crim_angle = 0

#delta time consistency solution is from a video
delta_time = 0.1
x = 30
y = 30
angle = 0
color = 0
counter = 0
crim_x = 100
crim_y = 100


while running:
    delta_time = clock.tick(60)/1000
    delta_time=max(0.001, min(0.1, delta_time))
    screen.fill((51,63,127))

    if color in range(0, 15):
        player_img = pg.image.load("MapIcon_10.png").convert_alpha()
        color += 1
    elif color in range (15, 30):
        player_img = pg.image.load("MapIcon_11.png").convert_alpha()
        color += 1
    else:
        color = 0
    player_cpy = pg.transform.rotate(player_img, angle)
    screen.blit(player_cpy, (x - int(player_cpy.get_width() / 2), y - int(player_cpy.get_height() / 2)))
    

    if counter in range (1, 150):
        counter +=1
    elif counter == 0:
        path = pathfinding.find_path(scrn_w - 5, scrn_h - 5, scrn_w - (scrn_w - 5), scrn_h - (scrn_h - 5), x, y )
        counter += 1
    else:
        path = pathfinding.find_path(scrn_w - 5, scrn_h - 5, scrn_w - (scrn_w - 5), scrn_h - (scrn_h - 5), x, y )
        counter = 1

    end_x, end_y = path

    theta = math.degrees(pathfinding.make_path(crim_x, crim_y, end_x, end_y))

    #claude did this line
    diff = (theta - crim_angle + 180) % 360 - 180

    turn = 90 * delta_time
    
    if diff > 0:
        mod = -1
    else:
        mod = 1
    
    if abs(diff) < turn:
        crim_angle = theta
    else:
        crim_angle += turn * mod

    if end_x == crim_x and end_y == crim_y:
        path = pathfinding.find_path(scrn_w - 5, scrn_h - 5, scrn_w - (scrn_w - 5), scrn_h - (scrn_h - 5), x, y )
        end_x, end_y = path

        theta = math.degrees(pathfinding.make_path(crim_x, crim_y, end_x, end_y))
        diff = (theta - crim_angle + 180) % 360 - 180

        turn = 90 * delta_time
        
        if diff > 0:
            mod = -1
        else:
            mod = 1
        
        if abs(diff) < turn:
            crim_angle = theta
        else:
            crim_angle += turn * mod


    crim_rad = math.radians(-crim_angle)
    crim_x += math.sin(crim_rad) * 4 * delta_time * 60 
    crim_y -= math.cos(crim_rad) * 4 * delta_time * 60
    
    criminal_cpy = pg.transform.rotate(criminal, crim_angle)
    screen.blit(criminal_cpy, (crim_x - int(criminal_cpy.get_width() / 2), crim_y - int(criminal_cpy.get_height() / 2)))
    
    x = max(player_img.get_width() / 2, min(scrn_w - (player_img.get_width() / 2), x))
    y = max(player_img.get_height() / 2, min(scrn_h - (player_img.get_height() / 2), y))
    
    
    crim_x = max(criminal.get_width() / 2, min(scrn_w - (criminal.get_width() / 2), crim_x))
    crim_y = max(criminal.get_height() / 2, min(scrn_h - (criminal.get_height() / 2), crim_y))


    if turning_right == True:
        angle -= 90*delta_time
    if turning_left == True:
        angle += 90*delta_time
    rad = math.radians(-angle)
    if moving_forward == True:
        x += math.sin(rad) * 3
        y -= math.cos(rad) * 3
    if moving_back == True:
        x -= math.sin(rad) * 3
        y += math.cos(rad) * 3
        
    for e in pg.event.get():
        if e.type == pg.QUIT:
            running = False
        if e.type == pg.KEYDOWN:
            if e.key == pg.K_RIGHT:
                turning_right = True
            if e.key == pg.K_LEFT:
                turning_left = True
            if e.key == pg.K_UP:
                moving_forward = True
            if e.key == pg.K_DOWN:
                moving_back = True
        if e.type == pg.KEYUP:
            if e.key == pg.K_RIGHT:
                turning_right = False
            if e.key == pg.K_LEFT:
                turning_left = False
            if e.key == pg.K_UP:
                moving_forward = False
            if e.key == pg.K_DOWN:
                moving_back = False

    pg.display.flip()