# import socket
# import logging

# # Configure logging
# logging.basicConfig(level=logging.INFO, format='[CLIENT] %(asctime)s - %(levelname)s - %(message)s')

# HOST = '127.0.0.1'
# PORT = 65432

# def connect_to_server(host, port):
#     client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
#     client_socket.connect((host, port))
#     logging.info(f"Connected to server at {host}:{port}")
#     return client_socket

# def send_and_receive(client_socket):
#     try:
#         while True:
#             msg = input("Enter message (or 'exit'): ")
#             if msg.lower() == 'exit':
#                 logging.info("Client exiting.")
#                 break

#             client_socket.sendall(msg.encode())
#             logging.info(f"Sent: {msg}")

#             data = client_socket.recv(1024)
#             logging.info(f"Received: {data.decode()}")
#     finally:
#         client_socket.close()
#         logging.info("Connection closed.")

# def run_client():
#     client_socket = connect_to_server(HOST, PORT)
#     send_and_receive(client_socket)

# def main():
#     run_client()

# if __name__ == "__main__":
#     main()