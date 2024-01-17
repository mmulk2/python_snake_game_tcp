import numpy as np
import socket
from _thread import *
import uuid
import time
import rsa
from snake import SnakeGame

# Function to generate a random color for the snake
def generate_random_color():
    rgb_colors = {
        "red": (255, 0, 0),
        "green": (0, 255, 0),
        "blue": (0, 0, 255),
        "yellow": (255, 255, 0),
        "orange": (255, 165, 0),
    }
    rgb_colors_list = list(rgb_colors.values())
    return rgb_colors_list[np.random.randint(0, len(rgb_colors_list))]

# Server configuration
s_server = "localhost"
s_port = 5555
s_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

# Number of rows in the SnakeGame
rows = 20

try:
    s_socket.bind((s_server, s_port))
except socket.error as e:
    print(str(e))

s_socket.listen()
print("...... Initiating Server ..... ")

# Create an instance of SnakeGame
s_game = SnakeGame(rows)
s_game_started = False
s_game_state = ""
s_interval = 0.2
s_moves_queue = set()
s_clients = {}  # Dictionary to hold client connections
s_clients_KEYS = {}  # Dictionary to hold public keys of clients

# Function to broadcast game state to all clients
def broadcast_GS():
    global s_game_state
    while True:
        s_game_state = s_game.get_state()
        for unique_id, s_client in list(s_clients.items()):  # Use list to safely modify during iteration
            try:
                s_client.sendall(s_game_state.encode())
            except:
                print(f"Disconnecting {unique_id}")
                s_client.close()
                del s_clients[unique_id]
                s_game.remove_player(unique_id)
        time.sleep(0.1)

# Function to broadcast a chat message to all clients
def broadcast_message(sender_id, message):
    print(f"User {sender_id} says: {message}")
    
    encrypted_prefix = f"MSG: User {sender_id} says: ".encode()

    for unique_id, s_client in s_clients.items():
        if unique_id != sender_id:
            try:
                encrypted_data = rsa.encrypt(encrypted_prefix + message.encode(), s_clients_KEYS[unique_id])
                s_client.sendall(encrypted_data)
            except Exception as e:
                print(f"Error sending message: {e}")

# Function to process data received from a client
def process_client_data(data, unique_id, priv_key):
    hotkeys = {
        'c': "Ready?",
        'x': "It works!",
        'z': "Congratulations!"
    }

    try:
        decMSG = rsa.decrypt(data, priv_key).decode()
        if not decMSG:
            raise Exception("Client disconnected")

        if decMSG in ["up", "down", "left", "right"]:
            handle_movement(unique_id, decMSG)
        elif decMSG == "reset":
            handle_reset(unique_id)
        elif decMSG in hotkeys:
            broadcast_message(unique_id, message=hotkeys[decMSG])

    except Exception as e:
        print(f"Error {unique_id}: {e}")

# Function to handle snake movement
def handle_movement(unique_id, direction):
    global s_moves_queue
    s_moves_queue.add((unique_id, direction))

# Function to handle resetting a player
def handle_reset(unique_id):
    global s_game
    s_game.reset_player(unique_id)

# Function to handle communication with a client
def Cthread(conn, unique_id, priv_key):
    global s_game
    try:
        while True:
            data = conn.recv(500)
            if not data:
                # Connection closed by the client
                break

            if data != b'get':
                process_client_data(data, unique_id, priv_key)
    except socket.error as e:
        print(f"Removing disconnected client: {unique_id}")
    except Exception as e:
        print(f"Error in client thread for {unique_id}: {e}")
    finally:
        # Clean up: Close the connection and remove the player
        conn.close()
        del s_clients[unique_id]
        s_game.remove_player(unique_id)

# Function to move and update the game state
def move_and_update_game():
    global s_moves_queue, s_game_state, s_interval
    s_game.move(s_moves_queue)
    s_moves_queue.clear()  # Use clear() for efficiency
    s_game_state = s_game.get_state()

# Function to run the game thread
def Gthread():
    while True:
        move_and_update_game()
        time.sleep(s_interval)

# Function to enter the game
def enter_game():
    global s_game_started
    if not s_game_started:
        s_game_started = True
        start_new_thread(Gthread, ())
        start_new_thread(broadcast_GS, ())

# Function to handle client connections
def handle_client_connection():
    global s_pub_key, s_priv_key, s_clients_KEYS

    while True:
        s_conn, s_addr = s_socket.accept()
        s_conn.send(s_pub_key.save_pkcs1())
        s_client_pub_key = rsa.PublicKey.load_pkcs1(s_conn.recv(2048))
        s_unique_id = str(uuid.uuid4())
        s_game.add_player(s_unique_id, color=generate_random_color())
        s_clients[s_unique_id] = s_conn
        s_clients_KEYS[s_unique_id] = s_client_pub_key
        print("Connected to:", s_addr)
        start_new_thread(Cthread, (s_conn, s_unique_id, s_priv_key))

# Function to initialize the server
def initialize_server():
    global s_pub_key, s_priv_key, s_clients_KEYS

    (s_pub_key, s_priv_key) = rsa.newkeys(2048)
    
    s_conn, s_addr = s_socket.accept()
    s_conn.send(s_pub_key.save_pkcs1())
    s_unique_id = str(uuid.uuid4())
    s_game.add_player(s_unique_id, color=generate_random_color())
    s_clients[s_unique_id] = s_conn
    s_client_pub_key = rsa.PublicKey.load_pkcs1(s_conn.recv(2048))
    s_clients_KEYS[s_unique_id] = s_client_pub_key
    print("Connected to:", s_addr)
    start_new_thread(Cthread, (s_conn, s_unique_id, s_priv_key))

# Main server function
def main_server():
    initialize_server()
    enter_game()
    handle_client_connection()

if __name__ == "__main__":
    main_server()
