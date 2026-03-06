import pygame as pg

pg.init()
pg.key.set_repeat(5, 5)
turning_right = False
moving_back = False
moving_forward = False
turning_left = False

clock = pg.time.Clock()
running = True
screen = pg.display.set_mode((1000, 1000))
player_img = pg.image.load("MapIcon_0.png").convert_alpha()
#delta time consistency solution is from a video
delta_time = 0.1
x = 30
y = 30
angle = 0
while running:
    screen.fill((51,63,127))
    clock.tick(60)
    screen.blit(player_img, (x, y))
    hitbox = pg.Rect(x, y, player_img.get_width(), player_img.get_height())
    
    #AI solution lines 26-28
    rotated_img = pg.transform.rotate(player_img, angle)
    screen.blit(rotated_img, (x, y))
    hitbox = pg.Rect(x, y, rotated_img.get_width(), rotated_img.get_height())
    
    if turning_right == True:
        angle += 90*delta_time
    if turning_left == True:
        angle -= 90*delta_time
    if moving_forward == True:
        y -=50*delta_time
    if moving_back == True:
        y +=50*delta_time
        
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
    delta_time = clock.tick(60)/1000
    delta_time=max(0.001, min(0.1, delta_time))
    
    pg.display.flip()