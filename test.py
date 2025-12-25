from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *
import math
import time
import random

# ===== HIGHWAY DASH 3D: COMBAT EDITION (Level Up Update) =====
WINDOW_WIDTH = 1200
WINDOW_HEIGHT = 800

# Game States
MENU = 0
RACING = 1
PAUSED = 2
FINISHED = 3
GAME_COMPLETE = 5
CUSTOM_RACE_MENU = 6

# Global variables
game_state = MENU
race_start_time = 0
last_time = time.time()

# Theme
cyberpunk_mode = True  

# Custom race settings
custom_laps = 1
custom_difficulty = 1  

# Game features
coins_collected = 0
current_level = 1
max_level = 3 
first_person_view = False
races_won = 0
current_lap = 1
total_laps = 1

# Track Config
ROAD_WIDTH = 1200
ROAD_LENGTH = 3000 + (current_level * 2000)
FINISH_LINE_POSITION = ROAD_LENGTH - 200

# Physics
FRICTION = 0.95
AIR_RESISTANCE = 0.99
MAX_SPEED_LIMIT = 50 

# Camera
camera_distance = 250
camera_height = 120

# Collectibles, Obstacles & Bullets
coin_positions = []
shield_token = None 
obstacles = []      
bullets = []        # [x, y, z, vx, vy]

# Auto restart
AUTO_RESTART_SECONDS = 3.0
game_complete_time = None

def generate_level_objects():
    """Generate Coins, Shield, and OBSTACLES based on LEVEL"""
    global coin_positions, shield_token, obstacles, bullets, current_level
    coin_positions = []
    obstacles = []
    bullets = [] # Clear bullets on new level
    
    # 1. Generate Coins
    y_pos = 200
    while y_pos < ROAD_LENGTH - 500:
        x_pos = random.uniform(-ROAD_WIDTH/3, ROAD_WIDTH/3)
        coin_positions.append([x_pos, y_pos, 30, True]) 
        y_pos += random.uniform(200, 500)

    # 2. Generate ONE Shield Token
    shield_x = random.uniform(-ROAD_WIDTH/3, ROAD_WIDTH/3)
    shield_y = random.uniform(ROAD_LENGTH * 0.3, ROAD_LENGTH * 0.8)
    shield_token = [shield_x, shield_y, 30, True]

    # 3. Generate Obstacles (SCALING DIFFICULTY)
    # Level 1: 8 obstacles
    # Level 2: 12 obstacles
    # Level 3: 16 obstacles
    num_obstacles = 8 + ((current_level - 1) * 4)

    for _ in range(num_obstacles):
        ox = random.uniform(-ROAD_WIDTH/3, ROAD_WIDTH/3)
        # Ensure obstacles are spread out over the new, longer road lengths
        oy = random.uniform(400, ROAD_LENGTH - 400)
        otype = random.choice([0, 1]) # 0 = Cube, 1 = Cone
        obstacles.append([ox, oy, 30, otype])

def detect_car_collision(car1, car2):
    """Detect collision between two jets"""
    dx = car1.x - car2.x
    dy = car1.y - car2.y
    distance = math.sqrt(dx**2 + dy**2)
    return distance < 80  

class Jet:
    def __init__(self, position, color, is_player=False):
        self.x, self.y, self.z = position
        self.velocity_x = 0
        self.velocity_y = 0
        self.rotation = 0 
        self.bank_angle = 0
        self.speed = 0
        
        self.max_speed = 14 if is_player else 9.5
        self.acceleration_power = 0.4
        
        self.braking_power = 1.5
        self.steering_power = 2.5
        self.color = color
        self.is_player = is_player
        self.finished = False
        self.lap_time = 0
        self.race_time = 0
        self.crashed = False
        self.laps_completed = 0
        self.has_shield = False
        
    def update(self, dt):
        global coins_collected, current_lap, game_state
        
        if self.crashed:
            if self.z > 0:
                self.z -= 2
                self.rotation += 10
            return
        
        # Stabilization
        self.velocity_x *= 0.92 
        self.velocity_y *= AIR_RESISTANCE
        
        # Banking
        target_bank = -self.velocity_x * 15
        self.bank_angle += (target_bank - self.bank_angle) * 0.1
        
        # Position
        self.x += self.velocity_x * dt * 60
        self.y += self.velocity_y * dt * 60
        self.z = 30 + math.sin(time.time() * 5 + self.x) * 2
        
        self.speed = math.sqrt(self.velocity_x**2 + self.velocity_y**2)
        
        if self.is_player:
            self.check_collisions()
        
        # Boundaries
        if abs(self.x) > ROAD_WIDTH / 2 - 50:
            self.velocity_x *= -0.5
            self.speed *= 0.8
            if self.x > 0:
                self.x = ROAD_WIDTH / 2 - 50
            else:
                self.x = -ROAD_WIDTH / 2 + 50
        
        # Lap logic
        if self.y >= FINISH_LINE_POSITION and not self.finished:
            self.laps_completed += 1
            if self.laps_completed >= total_laps:
                self.finished = True
                self.race_time = time.time() - race_start_time
            else:
                if self.is_player:
                    self.y = 50
                    current_lap = self.laps_completed + 1
                else:
                    self.y = random.uniform(50, 150)
    
    def check_collisions(self):
        global coins_collected, shield_token, game_state
        
        # 1. Coins
        for coin in coin_positions:
            if coin[3]:
                distance = math.sqrt((self.x - coin[0])**2 + (self.y - coin[1])**2 + (self.z - coin[2])**2)
                if distance < 60:
                    coin[3] = False
                    coins_collected += 1
        
        # 2. Shield
        if shield_token and shield_token[3]:
            dist = math.sqrt((self.x - shield_token[0])**2 + (self.y - shield_token[1])**2 + (self.z - shield_token[2])**2)
            if dist < 60:
                shield_token[3] = False
                self.has_shield = True

        # 3. OBSTACLES (Player Crash)
        for obs in obstacles:
            obs_dist = math.sqrt((self.x - obs[0])**2 + (self.y - obs[1])**2)
            if obs_dist < 60: # Hitbox
                if self.has_shield:
                    self.has_shield = False
                    obs[1] = -1000 # Remove obstacle effectively
                else:
                    self.crashed = True
                    game_state = FINISHED
    
    def accelerate(self):
        if not self.crashed and self.speed < self.max_speed:
            self.velocity_y += self.acceleration_power
    
    def brake(self):
        if not self.crashed and self.speed > 0.1:
            self.velocity_x *= 0.9
            self.velocity_y *= 0.9
    
    def steer_left(self):
        if not self.crashed and self.speed > 1:
            self.velocity_x -= self.steering_power * 0.3
            self.rotation = max(-25, self.rotation - 2)
    
    def steer_right(self):
        if not self.crashed and self.speed > 1:
            self.velocity_x += self.steering_power * 0.3
            self.rotation = min(25, self.rotation + 2)
    
    def center_rotation(self):
        if self.rotation > 0:
            self.rotation = max(0, self.rotation - 1)
        elif self.rotation < 0:
            self.rotation = min(0, self.rotation + 1)

# Game Objects
player_jet = Jet((0, 0, 30), (0.7, 0.7, 0.8), True) 
ai_jets = [
    Jet((-40, 50, 30), (0.8, 0.2, 0.2)), 
    Jet((40, 100, 30), (0.2, 0.8, 0.2)), 
    Jet((-20, 150, 30), (0.8, 0.8, 0.2)) 
]
all_jets = [player_jet] + ai_jets

# Input
keys = {
    b'w': False, b's': False, b'a': False, b'd': False,
    b' ': False, b'r': False, b'p': False, b'v': False,
    b'm': False
}

# --- FEATURE 4: FIRE BULLET ---
def fire_bullet():
    angle_rad = math.radians(player_jet.rotation)
    offset_x = -12 * math.sin(angle_rad)
    offset_y = 12 * math.cos(angle_rad)
    
    spawn_x = player_jet.x + offset_x
    spawn_y = player_jet.y + offset_y
    spawn_z = player_jet.z + 7
    
    bullet_speed = 800 
    vx = -math.sin(angle_rad) * bullet_speed
    vy = math.cos(angle_rad) * bullet_speed
    
    bullets.append([spawn_x, spawn_y, spawn_z, vx, vy])

def update_bullets(dt):
    global bullets, obstacles
    active_bullets = []
    for b in bullets:
        b[0] += b[3] * dt
        b[1] += b[4] * dt
        bullet_hit = False
        
        # Check collision with Obstacles
        for obs in obstacles:
            dist = math.sqrt((b[0] - obs[0])**2 + (b[1] - obs[1])**2)
            if dist < 35:
                bullet_hit = True
                obs[1] = -5000 
                break
        
        if not bullet_hit and 0 < b[1] < ROAD_LENGTH + 500:
            active_bullets.append(b)
            
    bullets = active_bullets

# ------------------------------

def draw_text_2d(x, y, text, size=18):
    glPushAttrib(GL_ALL_ATTRIB_BITS)
    glDisable(GL_DEPTH_TEST)
    glDisable(GL_LIGHTING)
    glMatrixMode(GL_PROJECTION)
    glPushMatrix()
    glLoadIdentity()
    gluOrtho2D(0, WINDOW_WIDTH, 0, WINDOW_HEIGHT)
    glMatrixMode(GL_MODELVIEW)
    glPushMatrix()
    glLoadIdentity()
    
    if cyberpunk_mode:
        glColor3f(0.0, 1.0, 1.0) 
    else:
        glColor3f(0.0, 1.0, 0.0) 
        
    glRasterPos2f(x, y)
    try:
        font = GLUT_BITMAP_HELVETICA_18 if size == 18 else GLUT_BITMAP_HELVETICA_12
        for char in text:
            glutBitmapCharacter(font, ord(char))
    except:
        for char in text:
            glutBitmapCharacter(GLUT_BITMAP_9_BY_15, ord(char))
    glPopMatrix()
    glMatrixMode(GL_PROJECTION)
    glPopMatrix()
    glMatrixMode(GL_MODELVIEW)
    glPopAttrib()

def draw_game_objects():
    # Draw Coins
    for coin in coin_positions:
        if coin[3]:
            glPushMatrix()
            glTranslatef(coin[0], coin[1], coin[2])
            glRotatef(time.time() * 100, 0, 0, 1)
            glRotatef(90, 1, 0, 0)
            if cyberpunk_mode:
                glColor3f(1.0, 0.0, 1.0) 
            else:
                glColor3f(0.0, 1.0, 0.0) 
            glutSolidTorus(2, 8, 8, 16)
            glPopMatrix()

    # Draw Shield Token
    if shield_token and shield_token[3]:
        glPushMatrix()
        glTranslatef(shield_token[0], shield_token[1], shield_token[2])
        glRotatef(time.time() * 50, 0, 1, 0) 
        glColor3f(0.0, 0.0, 1.0) # Blue Sphere
        glutSolidSphere(8, 16, 16)
        glPopMatrix()

    # Draw Obstacles (Only if they are on the map)
    for obs in obstacles:
        if obs[1] > -100: # Don't draw destroyed ones
            glPushMatrix()
            glTranslatef(obs[0], obs[1], obs[2])
            
            glColor3f(1.0, 0.0, 0.0) # Red
            
            if obs[3] == 0: # CUBE
                glutSolidCube(40)
            else: # CONE
                glRotatef(-90, 1, 0, 0)
                glutSolidCone(20, 60, 16, 16)
                
            glPopMatrix()
            
    # Draw Bullets
    for b in bullets:
        glPushMatrix()
        glTranslatef(b[0], b[1], b[2])
        glColor3f(1.0, 1.0, 0.0) # Yellow
        glutSolidSphere(3, 8, 8)
        glPopMatrix()

def draw_highway_road():
    if cyberpunk_mode:
        glColor3f(0.1, 0.0, 0.2) 
    else:
        glColor3f(0.0, 0.0, 0.0)
    
    glBegin(GL_QUADS)
    glVertex3f(-ROAD_WIDTH/2, 0, 0)
    glVertex3f(ROAD_WIDTH/2, 0, 0)
    glVertex3f(ROAD_WIDTH/2, ROAD_LENGTH, 0)
    glVertex3f(-ROAD_WIDTH/2, ROAD_LENGTH, 0)
    glEnd()
    
    light_spacing = 100
    y = 0
    while y < ROAD_LENGTH:
        if cyberpunk_mode:
            glColor3f(0, 1, 1) 
        else:
            glColor3f(0, 1, 0) 

        glPushMatrix()
        glTranslatef(-ROAD_WIDTH/2, y, 0)
        glutSolidSphere(3, 8, 8)
        glPopMatrix()
        
        glPushMatrix()
        glTranslatef(ROAD_WIDTH/2, y, 0)
        glutSolidSphere(3, 8, 8)
        glPopMatrix()
        y += light_spacing

    if cyberpunk_mode:
        glColor3f(0.0, 1.0, 1.0) 
    else:
        glColor3f(0.0, 1.0, 0.0) 
        
    glLineWidth(5)
    dash_length = 80
    gap_length = 80
    y_pos = 0
    while y_pos < ROAD_LENGTH:
        glBegin(GL_QUADS)
        glVertex3f(-5, y_pos, 1)
        glVertex3f(5, y_pos, 1)
        glVertex3f(5, min(y_pos + dash_length, ROAD_LENGTH), 1)
        glVertex3f(-5, min(y_pos + dash_length, ROAD_LENGTH), 1)
        glEnd()
        y_pos += dash_length + gap_length
    
    draw_game_objects()
    draw_finish_line()

def draw_finish_line():
    finish_y = FINISH_LINE_POSITION
    
    if cyberpunk_mode:
        glColor3f(1.0, 0.0, 1.0) 
    else:
        glColor3f(0.0, 1.0, 0.0) 

    for x in [-ROAD_WIDTH/2, ROAD_WIDTH/2]:
        glPushMatrix()
        glTranslatef(x, finish_y, 0)
        glRotatef(-90, 1, 0, 0)
        gluCylinder(gluNewQuadric(), 5, 5, 80, 10, 1)
        glPopMatrix()
    
    if cyberpunk_mode:
        glColor3f(0, 1, 1) 
    else:
        glColor3f(0, 0.5, 0) 
        
    glBegin(GL_QUADS)
    glVertex3f(-ROAD_WIDTH/2, finish_y, 70)
    glVertex3f(ROAD_WIDTH/2, finish_y, 70)
    glVertex3f(ROAD_WIDTH/2, finish_y, 80)
    glVertex3f(-ROAD_WIDTH/2, finish_y, 80)
    glEnd()

    glColor3f(1, 1, 1)
    segment_width = ROAD_WIDTH / 8
    for i in range(8):
        if i % 2 == 0:
            glBegin(GL_QUADS)
            x1 = -ROAD_WIDTH/2 + i * segment_width
            x2 = x1 + segment_width
            glVertex3f(x1, finish_y, 1)
            glVertex3f(x2, finish_y, 1)
            glVertex3f(x2, finish_y + 100, 1)
            glVertex3f(x1, finish_y + 100, 1)
            glEnd()

def draw_highway_environment():
    if cyberpunk_mode:
        glColor3f(0.1, 0.0, 0.2)
    else:
        glColor3f(0.0, 0.0, 0.0)
        
    glBegin(GL_QUADS)
    glVertex3f(-3000, 0, -5)
    glVertex3f(3000, 0, -5)
    glVertex3f(3000, ROAD_LENGTH + 1000, -5)
    glVertex3f(-3000, ROAD_LENGTH + 1000, -5)
    glEnd()

def draw_fighter_jet(jet):
    glPushMatrix()
    glTranslatef(jet.x, jet.y, jet.z)
    
    # Shield Effect
    if jet.has_shield:
        glPushMatrix()
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE) 
        glColor4f(0.0, 0.0, 1.0, 0.3) 
        glutSolidSphere(22, 24, 24) 
        glDisable(GL_BLEND)
        glPopMatrix()
    
    glRotatef(jet.rotation, 0, 0, 1)
    glRotatef(jet.bank_angle, 0, 1, 0)
    
    if jet.crashed:
        glColor3f(0.3, 0.3, 0.3)
    else:
        glColor3f(jet.color[0], jet.color[1], jet.color[2])
    
    glPushMatrix()
    glScalef(1.5, 5.0, 1.5) 
    glutSolidSphere(4, 12, 12)
    glPopMatrix()
    
    glPushMatrix()
    glTranslatef(0, 18, 0)
    glRotatef(-90, 1, 0, 0) 
    glColor3f(0.2, 0.2, 0.2) 
    glutSolidCone(3.5, 8, 10, 2)
    glPopMatrix()
    
    # GUN (Player Only)
    if jet.is_player:
        glPushMatrix()
        glTranslatef(0, 12, 7.0)
        glColor3f(0.2, 0.2, 0.2)
        glutSolidSphere(2.5, 10, 10)
        glRotatef(-90, 1, 0, 0) 
        glutSolidCone(1.5, 35, 10, 2)
        glPopMatrix()

    glPushMatrix()
    glTranslatef(0, 5, 4.0)
    glScalef(1.2, 3.0, 1.2)
    
    if cyberpunk_mode:
        glColor3f(0.0, 1.0, 1.0) 
    else:
        glColor3f(0.0, 1.0, 0.0) 
        
    glutSolidSphere(2, 8, 8)
    glPopMatrix()
    
    if not jet.crashed:
        glColor3f(jet.color[0]*0.9, jet.color[1]*0.9, jet.color[2]*0.9)
    
    glBegin(GL_TRIANGLES)
    glVertex3f(-3.5, 8, 0)    
    glVertex3f(-3.5, -8, 0)   
    glVertex3f(-25, -15, 0)   
    glVertex3f(3.5, 8, 0)    
    glVertex3f(3.5, -8, 0)    
    glVertex3f(25, -15, 0)    
    glVertex3f(-3, -15, 3)    
    glVertex3f(3, -15, 3)     
    glVertex3f(0, -20, 15)    
    glEnd()
    
    glPushMatrix()
    glTranslatef(0, -18, 0)
    glColor3f(0.2, 0.2, 0.2)
    glPushMatrix()
    glTranslatef(-2.5, 0, 0)
    glutSolidSphere(2.0, 6, 6)
    glPopMatrix()
    glPushMatrix()
    glTranslatef(2.5, 0, 0)
    glutSolidSphere(2.0, 6, 6)
    glPopMatrix()
    
    if not jet.crashed and jet.speed > 0.5:
        pulse = 1.0 + random.uniform(-0.2, 0.2)
        if cyberpunk_mode:
            glColor3f(1.0, 0.0, 1.0) 
        else:
            glColor3f(0.0, 1.0, 0.0) 

        glPushMatrix()
        glTranslatef(-2.5, -3, 0)
        glScalef(1.5, pulse * 4, 1.5)
        glutSolidSphere(1.0, 6, 6)
        glPopMatrix()
        glPushMatrix()
        glTranslatef(2.5, -3, 0)
        glScalef(1.5, pulse * 4, 1.5)
        glutSolidSphere(1.0, 6, 6)
        glPopMatrix()

    glPopMatrix() 
    glPopMatrix()

def update_ai_racers(dt):
    """AI with SCALABLE speed based on level"""
    for i, jet in enumerate(ai_jets):
        if jet.finished or jet.crashed:
            continue
        
        # --- MODIFIED SPEED LOGIC ---
        # Base difficulty + (Level * 0.15)
        # This gives a 15% speed boost per level
        difficulty_multiplier = 0.10 + (custom_difficulty * 0.01)
        ai_speed_multiplier = difficulty_multiplier + ((current_level - 1) * 0.15)
        
        if jet.speed < jet.max_speed:
            jet.velocity_y += jet.acceleration_power * ai_speed_multiplier
        
        current_time = time.time()
        
        if abs(jet.y - player_jet.y) < 200:
            if abs(jet.x - player_jet.x) < 120:
                if jet.x > player_jet.x:
                    jet.velocity_x += 0.3 
                else:
                    jet.velocity_x -= 0.3 
        
        elif int(current_time * 2 + i) % 20 == 0: 
            if abs(jet.x) < ROAD_WIDTH/3:
                steer_direction = 1 if jet.x < 0 else -1
                jet.velocity_x += steer_direction * 0.05 
        
        if abs(jet.x) > ROAD_WIDTH/3:
            jet.velocity_x -= jet.x * 0.05 
        
        jet.update(dt)

def update_highway_camera():
    if game_state == RACING:
        if first_person_view:
            glMatrixMode(GL_PROJECTION)
            glLoadIdentity()
            gluPerspective(70, WINDOW_WIDTH/WINDOW_HEIGHT, 1, 5000)
            glMatrixMode(GL_MODELVIEW)
            glLoadIdentity()
            forward_x = math.sin(math.radians(player_jet.rotation)) * -1 
            forward_y = math.cos(math.radians(player_jet.rotation))
            gluLookAt(player_jet.x, player_jet.y + 10, player_jet.z + 5,
                      player_jet.x + forward_x * 100, player_jet.y + 100, player_jet.z,
                      0, 0, 1)
        else:
            target_x = player_jet.x * 0.8 
            target_y = player_jet.y - camera_distance
            target_z = player_jet.z + camera_height
            glMatrixMode(GL_PROJECTION)
            glLoadIdentity()
            gluPerspective(60, WINDOW_WIDTH/WINDOW_HEIGHT, 1, 5000)
            glMatrixMode(GL_MODELVIEW)
            glLoadIdentity()
            gluLookAt(target_x, target_y, target_z,
                      player_jet.x, player_jet.y + 100, player_jet.z,
                      0, 0, 1)

def draw_dashboard_hud():
    if game_state != RACING and game_state != PAUSED:
        return
    
    if player_jet.crashed:
        draw_text_2d(WINDOW_WIDTH//2 - 50, WINDOW_HEIGHT//2, "CRASHED!")
        return
    
    speed_knots = int(player_jet.speed * 20)
    draw_text_2d(20, WINDOW_HEIGHT - 40, f"Airspeed: {speed_knots} Knots")
    draw_text_2d(20, WINDOW_HEIGHT - 70, f"Lap: {current_lap}/{total_laps}")
    draw_text_2d(20, WINDOW_HEIGHT - 100, f"Score: {coins_collected}")
    draw_text_2d(20, WINDOW_HEIGHT - 130, f"Level: {current_level}/{max_level}")
    
    shield_status = "ACTIVE" if player_jet.has_shield else "OFFLINE"
    draw_text_2d(20, WINDOW_HEIGHT - 160, f"SHIELD: {shield_status}")
    
    theme_text = "CYBERPUNK" if cyberpunk_mode else "STANDARD"
    draw_text_2d(20, WINDOW_HEIGHT - 190, f"Theme: {theme_text}")
    
    distance_remaining = max(0, FINISH_LINE_POSITION - player_jet.y)
    draw_text_2d(20, WINDOW_HEIGHT - 220, f"Distance: {int(distance_remaining)}m")
    
    if race_start_time > 0:
        current_race_time = time.time() - race_start_time
        draw_text_2d(20, WINDOW_HEIGHT - 250, f"Time: {current_race_time:.1f}s")
    
    position = 1
    for jet in ai_jets:
        if jet.y > player_jet.y and not jet.crashed:
            position += 1
    draw_text_2d(20, WINDOW_HEIGHT - 280, f"Rank: {position}/4")
    draw_text_2d(WINDOW_WIDTH - 250, WINDOW_HEIGHT - 30, "JET RACER 3D")
    draw_text_2d(WINDOW_WIDTH - 300, WINDOW_HEIGHT - 60, "W/S: Throttle")
    draw_text_2d(WINDOW_WIDTH - 300, WINDOW_HEIGHT - 80, "A/D: Bank Left/Right")
    draw_text_2d(WINDOW_WIDTH - 300, WINDOW_HEIGHT - 100, "M: Switch Theme")
    draw_text_2d(WINDOW_WIDTH - 300, WINDOW_HEIGHT - 120, "V: Camera | Click: Shoot")

def draw_main_menu():
    if cyberpunk_mode:
        glClearColor(0.05, 0.0, 0.1, 1) # Dark Purple
    else:
        glClearColor(0.0, 0.0, 0.0, 1) # Pure Black
        
    draw_text_2d(WINDOW_WIDTH//2 - 90, WINDOW_HEIGHT//2 + 200, "JET RACER 3D")
    draw_text_2d(WINDOW_WIDTH//2 - 150, WINDOW_HEIGHT//2 + 170, "==========================")
    draw_text_2d(WINDOW_WIDTH//2 - 100, WINDOW_HEIGHT//2 + 120, "Combat Edition")
    
    theme_status = f"Theme: {'Cyberpunk' if cyberpunk_mode else 'Standard (Retro)'}"
    draw_text_2d(WINDOW_WIDTH//2 - 100, WINDOW_HEIGHT//2 + 80, theme_status)
    
    draw_text_2d(WINDOW_WIDTH//2 - 100, WINDOW_HEIGHT//2 + 50, f"Current Level: {current_level}/{max_level}")
    draw_text_2d(WINDOW_WIDTH//2 - 100, WINDOW_HEIGHT//2 + 30, f"Total Score: {coins_collected}")
    draw_text_2d(WINDOW_WIDTH//2 - 100, WINDOW_HEIGHT//2 - 10, "Press SPACE to Scramble")
    
    draw_text_2d(WINDOW_WIDTH//2 - 100, WINDOW_HEIGHT//2 - 40, "Press B for Briefing (Custom)")
    
    draw_text_2d(WINDOW_WIDTH//2 - 100, WINDOW_HEIGHT//2 - 70, "ESC to Abort")
    draw_text_2d(WINDOW_WIDTH//2 - 100, WINDOW_HEIGHT//2 - 110, "Press M to Toggle Theme")

def draw_custom_race_menu():
    if cyberpunk_mode:
        glClearColor(0.1, 0.0, 0.15, 1)
    else:
        glClearColor(0.05, 0.05, 0.05, 1)
        
    draw_text_2d(WINDOW_WIDTH//2 - 100, WINDOW_HEIGHT//2 + 150, "CUSTOM SORTIE")
    draw_text_2d(WINDOW_WIDTH//2 - 130, WINDOW_HEIGHT//2 + 120, "==========================")
    draw_text_2d(WINDOW_WIDTH//2 - 80, WINDOW_HEIGHT//2 + 60, f"Laps: {custom_laps}")
    draw_text_2d(WINDOW_WIDTH//2 - 80, WINDOW_HEIGHT//2 + 40, "Press 1/2/3 for 1/3/5 laps")
    difficulties = ["Cadet", "Pilot", "Ace"]
    draw_text_2d(WINDOW_WIDTH//2 - 80, WINDOW_HEIGHT//2, f"Difficulty: {difficulties[custom_difficulty-1]}")
    draw_text_2d(WINDOW_WIDTH//2 - 80, WINDOW_HEIGHT//2 - 20, "Press Q/W/E for Cadet/Pilot/Ace")
    
    theme_status = f"Theme: {'Cyberpunk' if cyberpunk_mode else 'Standard'}"
    draw_text_2d(WINDOW_WIDTH//2 - 80, WINDOW_HEIGHT//2 - 80, theme_status)
    draw_text_2d(WINDOW_WIDTH//2 - 80, WINDOW_HEIGHT//2 - 100, "Press M to toggle Theme")
    
    draw_text_2d(WINDOW_WIDTH//2 - 80, WINDOW_HEIGHT//2 - 140, "Press SPACE to Launch")
    draw_text_2d(WINDOW_WIDTH//2 - 80, WINDOW_HEIGHT//2 - 160, "Press ESC to return")

def draw_game_complete():
    if cyberpunk_mode:
        glClearColor(0.1, 0.0, 0.2, 1)
    else:
        glClearColor(0.0, 0.1, 0.0, 1)
        
    center_x = WINDOW_WIDTH // 2
    center_y = WINDOW_HEIGHT // 2
    draw_text_2d(center_x - 120, center_y + 150, "MISSION ACCOMPLISHED!", 18)
    draw_text_2d(center_x - 90, center_y + 120, "CAMPAIGN FINISHED!", 18)
    draw_text_2d(center_x - 150, center_y + 90, f"YOU COMPLETED ALL {max_level} ZONES!", 18)
    draw_text_2d(center_x - 80, center_y + 50, "Top Gun!", 18)
    draw_text_2d(center_x - 120, center_y + 10, f"Total Score: {coins_collected}", 18)
    draw_text_2d(center_x - 100, center_y - 20, f"Total Victories: {races_won}", 18)
    if game_complete_time is not None:
        remaining_time = max(0, AUTO_RESTART_SECONDS - (time.time() - game_complete_time))
        draw_text_2d(center_x - 140, center_y - 60, f"Restarting Campaign in {remaining_time:.1f} seconds...", 18)
    else:
        draw_text_2d(center_x - 100, center_y - 60, "Thanks for Playing!", 18)
        draw_text_2d(center_x - 130, center_y - 90, "Press ESC to return to base", 18)

def handle_highway_controls(dt):
    global first_person_view
    if game_state != RACING:
        return
    if keys[b'w']:
        player_jet.accelerate()
    if keys[b's']:
        player_jet.brake()
    if keys[b'a']:
        player_jet.steer_left()
    if keys[b'd']:
        player_jet.steer_right()
    if not keys[b'a'] and not keys[b'd']:
        player_jet.center_rotation()

# --- FEATURE 4: MOUSE CLICK TO SHOOT ---
def mouse_click(button, state, x, y):
    if button == GLUT_LEFT_BUTTON and state == GLUT_DOWN:
        if game_state == RACING and not player_jet.crashed:
            fire_bullet()

def initialize_race_cars():
    player_jet.x, player_jet.y, player_jet.z = 0, 0, 30
    player_jet.velocity_x = player_jet.velocity_y = 0
    player_jet.rotation = 0
    player_jet.bank_angle = 0
    player_jet.finished = False
    player_jet.crashed = False
    player_jet.laps_completed = 0
    player_jet.speed = 0
    
    player_jet.has_shield = False
    
    ai_starting_positions = [
        (-180, 150, 30), 
        (180, 150, 30),  
        (0, 300, 30)     
    ]
    for i, jet in enumerate(ai_jets):
        if i < len(ai_starting_positions):
            jet.x, jet.y, jet.z = ai_starting_positions[i]
        else:
            jet.x, jet.y, jet.z = random.uniform(-100, 100), random.uniform(200, 400), 30
        jet.velocity_x = jet.velocity_y = 0
        jet.rotation = 0
        jet.bank_angle = 0
        jet.finished = False
        jet.crashed = False
        jet.laps_completed = 0
        jet.speed = 0

def keyboard_down(key, x, y):
    global game_state, race_start_time, first_person_view, current_level, ROAD_LENGTH, FINISH_LINE_POSITION
    global cyberpunk_mode, custom_laps, custom_difficulty, total_laps, current_lap
    
    if key == b'm':
        cyberpunk_mode = not cyberpunk_mode
        
    if game_state == GAME_COMPLETE:
        game_state = MENU
        return
        
    elif game_state == CUSTOM_RACE_MENU:
        if key == b'1': custom_laps = 1
        elif key == b'2': custom_laps = 3
        elif key == b'3': custom_laps = 5
        elif key == b'q': custom_difficulty = 1
        elif key == b'w': custom_difficulty = 2
        elif key == b'e': custom_difficulty = 3
        elif key == b' ':
            total_laps = custom_laps
            current_lap = 1
            game_state = RACING
            race_start_time = time.time()
            ROAD_LENGTH = 3000 + (current_level * 2000)
            FINISH_LINE_POSITION = ROAD_LENGTH - 200
            generate_level_objects()
            initialize_race_cars()
        elif key == b'\x1b':
            game_state = MENU
            
    elif key == b' ':
        if game_state == MENU:
            total_laps = 1
            current_lap = 1
            game_state = RACING
            race_start_time = time.time()
            ROAD_LENGTH = 3000 + (current_level * 2000)
            FINISH_LINE_POSITION = ROAD_LENGTH - 200
            generate_level_objects()
            initialize_race_cars()
            
    elif key == b'b' and game_state == MENU:
        game_state = CUSTOM_RACE_MENU
        
    elif key == b'p' and game_state == RACING:
        game_state = PAUSED
    elif key == b'p' and game_state == PAUSED:
        game_state = RACING
        
    elif key == b'v' and game_state == RACING:
        first_person_view = not first_person_view
    
    elif key == b'r':
        restart_highway_race()
    elif key == b'\x1b':
        if game_state == CUSTOM_RACE_MENU:
            game_state = MENU
        elif game_state == FINISHED:
            game_state = MENU
        elif game_state == GAME_COMPLETE:
            game_state = MENU
        elif game_state == MENU:
            try:
                glutLeaveMainLoop()
            except:
                import sys
                sys.exit(0)
        else:
            game_state = MENU
    if key in keys:
        keys[key] = True

def keyboard_up(key, x, y):
    if key in keys:
        keys[key] = False

def level_up():
    global current_level, races_won, game_state, game_complete_time
    races_won += 1
    current_level += 1
    if current_level > max_level:
        game_state = GAME_COMPLETE
        game_complete_time = time.time()
        current_level = max_level
        return

def restart_highway_race():
    global game_state, race_start_time, coins_collected, current_lap
    current_lap = 1
    initialize_race_cars()
    generate_level_objects()
    game_state = RACING
    race_start_time = time.time()

def reset_to_new_game():
    global current_level, races_won, coins_collected, game_state
    current_level = 1
    races_won = 0
    coins_collected = 0
    global ROAD_LENGTH, FINISH_LINE_POSITION
    ROAD_LENGTH = 3000 + (current_level * 2000)
    FINISH_LINE_POSITION = ROAD_LENGTH - 200
    game_state = MENU

def update_highway_game(dt):
    global game_state
    if game_state == RACING:
        handle_highway_controls(dt)
        # Check Jet Collision
        for i, jet1 in enumerate(all_jets):
            if jet1.crashed:
                continue
            for j, jet2 in enumerate(all_jets):
                if i >= j or jet2.crashed:
                    continue
                if detect_car_collision(jet1, jet2):
                    jet1.crashed = True
                    jet2.crashed = True
                    if jet1.is_player or jet2.is_player:
                        game_state = FINISHED
                        return
        player_jet.update(dt)
        update_bullets(dt) # Move bullets
        update_ai_racers(dt)
        if player_jet.finished:
            player_won = True
            for jet in ai_jets:
                if jet.finished and not jet.crashed and jet.race_time < player_jet.race_time:
                    player_won = False
                    break
            if player_won:
                level_up()
            game_state = FINISHED

def display():
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    if game_state == MENU:
        draw_main_menu()
    elif game_state == CUSTOM_RACE_MENU:
        draw_custom_race_menu()
    elif game_state == GAME_COMPLETE:
        draw_game_complete()
    elif game_state == RACING or game_state == PAUSED:
        if cyberpunk_mode:
            glClearColor(0.1, 0.0, 0.2, 1) 
        else:
            glClearColor(0.0, 0.0, 0.0, 1) 
            
        update_highway_camera()
        glEnable(GL_DEPTH_TEST)
        draw_highway_environment()
        draw_highway_road()
        if first_person_view:
            for jet in ai_jets:
                draw_fighter_jet(jet)
        else:
            for jet in all_jets:
                draw_fighter_jet(jet)
        glDisable(GL_DEPTH_TEST)
        draw_dashboard_hud()
        if game_state == PAUSED:
            draw_text_2d(WINDOW_WIDTH//2 - 50, WINDOW_HEIGHT//2, "PAUSED")
    elif game_state == FINISHED:
        if player_jet.crashed:
            draw_text_2d(WINDOW_WIDTH//2 - 80, WINDOW_HEIGHT//2 + 60, "MAYDAY! CRASHED!")
            draw_text_2d(WINDOW_WIDTH//2 - 100, WINDOW_HEIGHT//2 + 30, "Mid-air collision detected!")
        else:
            player_won = True
            for jet in ai_jets:
                if jet.finished and not jet.crashed and jet.race_time < player_jet.race_time:
                    player_won = False
                    break
            if player_won:
                if current_level >= max_level:
                    draw_text_2d(WINDOW_WIDTH//2 - 80, WINDOW_HEIGHT//2 + 60, "CAMPAIGN COMPLETE")
                else:
                    draw_text_2d(WINDOW_WIDTH//2 - 60, WINDOW_HEIGHT//2 + 60, "ZONE CLEARED")
                    draw_text_2d(WINDOW_WIDTH//2 - 100, WINDOW_HEIGHT//2 + 30, f"Advancing to Level {current_level}!")
                draw_text_2d(WINDOW_WIDTH//2 - 80, WINDOW_HEIGHT//2 - 20, f"Score: {coins_collected}")
            else:
                draw_text_2d(WINDOW_WIDTH//2 - 60, WINDOW_HEIGHT//2 + 30, "MISSION FAILED")
                draw_text_2d(WINDOW_WIDTH//2 - 80, WINDOW_HEIGHT//2, "You were outflown!")
        if player_jet.finished:
            draw_text_2d(WINDOW_WIDTH//2 - 80, WINDOW_HEIGHT//2 - 50, f"Time: {player_jet.race_time:.2f}s")
        draw_text_2d(WINDOW_WIDTH//2 - 80, WINDOW_HEIGHT//2 - 80, "Press R to Retry")
        draw_text_2d(WINDOW_WIDTH//2 - 80, WINDOW_HEIGHT//2 - 110, "Press ESC for Base")
    glutSwapBuffers()

def idle():
    global last_time, game_complete_time
    current_time = time.time()
    dt = min(current_time - last_time, 0.1)
    last_time = current_time
    if game_state == GAME_COMPLETE and game_complete_time is not None:
        if (current_time - game_complete_time) >= AUTO_RESTART_SECONDS:
            reset_to_new_game()
    update_highway_game(dt)
    glutPostRedisplay()

def main():
    generate_level_objects()
    glutInit()
    glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGB | GLUT_DEPTH)
    glutInitWindowSize(WINDOW_WIDTH, WINDOW_HEIGHT)
    glutCreateWindow(b"Jet Racer 3D - Combat")
    glEnable(GL_DEPTH_TEST)
    glEnable(GL_LIGHTING)
    glEnable(GL_LIGHT0)
    glLightfv(GL_LIGHT0, GL_POSITION, [100, 100, 200, 1])
    glEnable(GL_COLOR_MATERIAL)
    glutDisplayFunc(display)
    glutKeyboardFunc(keyboard_down)
    glutMouseFunc(mouse_click) # Register Mouse Function
    try:
        glutKeyboardUpFunc(keyboard_up)
    except:
        pass
    glutIdleFunc(idle)
    print("JET RACER 3D LAUNCHED")
    glutMainLoop()

if __name__ == "__main__":
    main()