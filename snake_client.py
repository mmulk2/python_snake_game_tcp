import socket
import pygame
import sys
import time
import numpy as np
import rsa

# Cube class represents individual cubes in the game grid
class Cube:
    rows = 20
    w = 500

    def __init__(self, start, dirnx=1, dirny=0, color=(255, 0, 0)):
        self.pos = start
        self.dirnx = dirnx
        self.dirny = dirny
        self.color = color

    def move(self, dirnx, dirny):
        self.dirnx = dirnx
        self.dirny = dirny
        self.pos = (self.pos[0] + self.dirnx, self.pos[1] + self.dirny)

    def draw(self, surface, eyes=False):
        dis = self.w // self.rows
        i, j = self.pos[0], self.pos[1]

        # Draw the cube on the game surface
        pygame.draw.rect(surface, self.color, (i * dis + 1, j * dis + 1, dis - 2, dis - 2))

        # Draw eyes if specified
        if eyes:
            self.draw_eyes(surface, i, j, dis)

    def draw_eyes(self, surface, i, j, dis):
        centre = dis // 2
        radius = 3
        circle_middle = (i * dis + centre - radius, j * dis + 8)
        circle_middle2 = (i * dis + dis - radius * 2, j * dis + 8)

        # Draw eyes on the cube
        pygame.draw.circle(surface, (0, 0, 0), circle_middle, radius)
        pygame.draw.circle(surface, (0, 0, 0), circle_middle2, radius)

# Snake class represents the snake in the game
class Snake:
    def __init__(self, color=None, positions=None):
        self.color = color or SnakeG().get_random_color()
        self.body = [Cube(pos, color=self.color) for pos in (positions or [])]

    def draw(self, surface):
        # Draw each cube in the snake's body
        for cube in self.body:
            cube.draw(surface)

# SnakeG class contains game configuration and drawing functions
class SnakeG:
    def __init__(self):
        self.width = 500
        self.rows = 20
        self.window = pygame.display.set_mode((self.width, self.width))
        self.red = (255, 0, 0)
        self.green = (0, 255, 0)
        self.rgb_colors = {
            "red": (255, 0, 0),
            "green": (0, 255, 0),
            "blue": (0, 0, 255),
            "yellow": (255, 255, 0),
            "orange": (255, 165, 0),
        }
        self.rgb_colors_list = list(self.rgb_colors.values())
        self.color = self.rgb_colors_list[np.random.randint(0, len(self.rgb_colors_list))]

    def draw_grid(self):
        # Draw grid lines on the game window
        size_between = self.width // self.rows
        for line in range(self.rows):
            x = y = line * size_between
            pygame.draw.line(self.window, (255, 255, 255), (x, 0), (x, self.width))
            pygame.draw.line(self.window, (255, 255, 255), (0, y), (self.width, y))

    def redraw_window(self, snake_body, snacks):
        self.window.fill((0, 0, 0))
        self.draw_grid()
        self.draw_snakes(snake_body)
        self.draw_snacks(snacks)
        pygame.display.update()

    def draw_snakes(self, snakes_bodies):
        dis = self.width // self.rows

        for snake_body in snakes_bodies.split('**'):
            try:
                # Step 1: Split the snake body into segments using '*'
                rawPortion = snake_body.split('*')

                # Step 2: Strip parentheses and split each segment by comma
                rawPortion_stripped = [segment.strip("()").split(",") for segment in rawPortion]

                # Step 3: Convert each pair of strings to integers and create tuples
                snake_portion = [tuple(map(int, segment)) for segment in rawPortion_stripped]

                # Usage:
                getPortionForSnake = snake_portion

                for index, (x, y) in enumerate(getPortionForSnake):
                    # Draw each cube in the snake's body
                    pygame.draw.rect(self.window, self.color, pygame.Rect(x * dis + 1, y * dis + 1, dis - 1, dis - 1))

                    # Draw the head of the snake
                    if index == 0:
                        self.draw_head(x, y, dis)

            except (ValueError, IndexError):
                print(f' Exception: {ValueError}')

    def draw_head(self, x, y, dis):
        centre = dis // 2
        radius = 3

        getPos = [
            (x * dis + centre - radius, y * dis + 8),
            (x * dis + dis - radius * 2, y * dis + 8)
        ]

        # Draw eyes on the snake's head
        pygame.draw.circle(self.window, (0, 0, 0), getPos[0], radius)
        pygame.draw.circle(self.window, (0, 0, 0), getPos[1], radius)

    def draw_snacks(self, snacks):
        dis = self.width // self.rows

        def parse_snack_position(snack):
            return tuple(map(int, snack.strip("()").split(",")))

        snack_positions = map(parse_snack_position, snacks.split('**'))

        # Draw each snack on the game window
        for x, y in snack_positions:
            snack_rect = pygame.Rect(x * dis + 1, y * dis + 1, dis - 1, dis - 1)
            pygame.draw.rect(self.window, self.green, snack_rect)

    def get_random_color(self):
        return np.random.choice(list(self.rgb_colors.values()))

# SnakeClient class manages the connection to the server
class SnakeClient:
    def __init__(self, server_address, port):
        self.server_address = server_address
        self.port = port
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.snakes = []
        self.snacks = []

    def connect_to_server(self):
        try:
            # Attempt to connect to the server
            self.client_socket.connect((self.server_address, self.port))
        except (socket.error, Exception) as e:
            print(f"Error connecting to the server: {e}")
            sys.exit(1)

# Extracts the new snake data by finding the first differing character
def extract_new_snake_data(prev, curr):
    min_length = min(len(prev), len(curr))
    getI = min_length
    for i in range(min_length):
        if prev[i] != curr[i]:
            getI = i
            break
        elif i == min_length - 1:
            getI = min_length

    return curr[getI:]

# Handles snake chat messages by printing the message content
def handle_snake_chat_message(message):
    prefix_length = 4
    print(message[prefix_length:])

# Handles snake key events by encrypting and sending the action to the server
def handle_snake_key_event(event, snake_client, snake_server_pub_key):
    global running

    # Define a set for faster key lookup
    valid_keys = {
        pygame.K_LEFT, pygame.K_RIGHT, pygame.K_UP,
        pygame.K_DOWN, pygame.K_r, pygame.K_q,
        pygame.K_x, pygame.K_z, pygame.K_c
    }

    # Check if the pressed key is in the set
    if event.key in valid_keys:
        action = {
            pygame.K_LEFT: 'left',
            pygame.K_RIGHT: 'right',
            pygame.K_UP: 'up',
            pygame.K_DOWN: 'down',
            pygame.K_r: 'reset',
            pygame.K_q: 'quit',
            pygame.K_x: 'x',
            pygame.K_z: 'z',
            pygame.K_c: 'c'
        }[event.key]

        # Encrypt and send the action to the server
        encrypted_data = rsa.encrypt(action.encode(), snake_server_pub_key)
        snake_client.send(encrypted_data)

        # If the 'quit' key is pressed, stop the game
        if event.key == pygame.K_q:
            running = False

# Connects to the snake server and initializes the game loop
def connect_to_snake_server(host='localhost', port=5555):
    snake_client = SnakeClient(host, port)
    snake_client.connect_to_server()
    return snake_client

# Main function for the snake client
def main_snake_client():
    pygame.init()
    snake_game_config = SnakeG()
    snake_client = connect_to_snake_server()
    time.sleep(1)

    # Generate public and private keys for secure communication
    snake_client_pub_key, snake_client_priv_key = rsa.newkeys(2048)
    snake_server_pub_key = rsa.PublicKey.load_pkcs1(snake_client.client_socket.recv(2048))
    snake_client.client_socket.send(snake_client_pub_key.save_pkcs1())

    global running
    running = True
    clock = pygame.time.Clock()
    getPrevData = ""

    while running:
        clock.tick(1000)

        try:
            # Request the game state from the server
            snake_client.client_socket.send(str.encode('get'))
            getNewData = snake_client.client_socket.recv(2048)

            try:
                # Attempt to decode the received data
                convertedMsg = getNewData.decode()
                game_state = convertedMsg
                snake_body, snacks = game_state.split('|')
                snake_client.client_socket.send(str.encode('get'))
                gameClient = snake_client.client_socket.recv(2048).decode()
                currMsg = extract_new_snake_data(getPrevData, gameClient)

                if currMsg:
                    getPrevData = gameClient

                else:
                    raise ValueError("Wrong character")

            except (UnicodeDecodeError, ValueError):
                # Decrypt the data if decoding fails
                decryptData = rsa.decrypt(getNewData, snake_client_priv_key).decode()
                if decryptData.startswith("MSG: "):
                    handle_snake_chat_message(decryptData)

        except Exception as e:
            continue

        # Handle user input events
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                snake_client.client_socket.send(str.encode('quit'))
            elif event.type == pygame.KEYDOWN:
                handle_snake_key_event(event, snake_client.client_socket, snake_server_pub_key)

        # Redraw the game window based on the updated game state
        snake_game_config.redraw_window(snake_body, snacks)

    # Clean up resources and close the connection
    pygame.quit()
    snake_client.client_socket.close()

if __name__ == "__main__":
    main_snake_client()
