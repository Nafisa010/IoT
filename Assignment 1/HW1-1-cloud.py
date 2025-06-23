import socket
import matplotlib
matplotlib.use('TkAgg')  # Use TkAgg backend
import matplotlib.pyplot as plt
from datetime import datetime

# Server configuration
SERVER_IP = 'localhost'
PORT_MCU1 = 4444  # Port for MCU1
PORT_MCU2 = 5555  # Port for MCU2
BUFF_SIZE = 1024
TEMP_THRESHOLD = 38  # Temperature threshold for fan control
CO_THRESHOLD = 20

# Lists to store data for plotting
timestamps = []
temperatures = []
co_levels = []
fan_states = []  # Will store 1 for "ON", 0 for "OFF"
window_states = []  # Will store 1 for "OPEN", 0 for "CLOSE"

# Create and set up the real-time plot
plt.ion()  # Enable interactive mode
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8))
fig.tight_layout(pad=5.0)

# Configure first plot (Temperature and CO)
temp_line, = ax1.plot([], [], 'g-', label='Temperature (°C)', linewidth=2)
co_line, = ax1.plot([], [], 'r-', label='CO Level', linewidth=2)
ax1.set_xlabel('Time (seconds)')
ax1.set_ylabel('Value')
ax1.set_title('Temperature and CO Levels')
ax1.grid(True)
ax1.legend()

# Configure second plot (Fan and Window Status)
fan_line, = ax2.plot([], [], 'b-', label='Fan Status', drawstyle='steps-post', linewidth=2)
window_line, = ax2.plot([], [], 'y-', label='Window Status', drawstyle='steps-post', linewidth=2)
ax2.set_xlabel('Time (seconds)')
ax2.set_ylabel('Status')
ax2.set_title('Fan and Window Status')
ax2.grid(True)
ax2.set_ylim(-0.1, 1.1)
ax2.legend()

# Force the plot window to open
plt.show(block=False)

# Create sockets for both MCUs
socket_mcu1 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
socket_mcu2 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

# Bind sockets
socket_mcu1.bind((SERVER_IP, PORT_MCU1))
socket_mcu2.bind((SERVER_IP, PORT_MCU2))

# Listen for MCU1
print(f"Waiting for MCU1 on port {PORT_MCU1}...")
socket_mcu1.listen(1)
mcu1_socket, mcu1_address = socket_mcu1.accept()
print(f"MCU1 connected from {mcu1_address}")

# Listen for MCU2
print(f"Waiting for MCU2 on port {PORT_MCU2}...")
socket_mcu2.listen(1)
mcu2_socket, mcu2_address = socket_mcu2.accept()
print(f"MCU2 connected from {mcu2_address}")

start_time = datetime.now()


def update_plot():
    """Update the real-time plot with current data."""
    # Update data
    temp_line.set_data(timestamps, temperatures)
    co_line.set_data(timestamps, co_levels)
    fan_line.set_data(timestamps, fan_states)
    window_line.set_data(timestamps, window_states)

    # Adjust axes limits
    if timestamps:
        # X-axis: show last 30 seconds of data
        xmin = max(0, timestamps[-1] - 60)
        xmax = timestamps[-1] + 2
        ax1.set_xlim(xmin, xmax)
        ax2.set_xlim(xmin, xmax)

        # Y-axis for temperature and CO
        if temperatures and co_levels:
            ymin = min(min(temperatures), min(co_levels)) - 1
            ymax = max(max(temperatures), max(co_levels)) + 1
            ax1.set_ylim(ymin, ymax)

    # Refresh the plot
    fig.canvas.draw_idle()
    plt.pause(0.5)  # Increase pause time to allow plot update


try:
    while True:
        # Get temperature data from MCU1
        temp_data = mcu1_socket.recv(BUFF_SIZE).decode().strip()
        if temp_data:
            print(f"Received from MCU1: {temp_data}")

            try:
                # Parse data
                temp_str, co_str = temp_data.split(',')
                temp_value = float(temp_str)
                CO_value = float(co_str)

                print(f"Parsed Temperature: {temp_value}, CO Level: {CO_value}")

                # Store data for plotting
                current_time = (datetime.now() - start_time).total_seconds()
                timestamps.append(current_time)
                temperatures.append(temp_value)
                co_levels.append(CO_value)

                # Determine commands
                command1 = "ON" if temp_value > TEMP_THRESHOLD else "OFF"
                command2 = "OPEN" if temp_value < TEMP_THRESHOLD else "CLOSE"

                # Update states
                fan_states.append(1 if command1 == "ON" else 0)
                window_states.append(1 if command2 == "OPEN" else 0)

                # Limit data points
                max_points = 100
                if len(timestamps) > max_points:
                    timestamps = timestamps[-max_points:]
                    temperatures = temperatures[-max_points:]
                    co_levels = co_levels[-max_points:]
                    fan_states = fan_states[-max_points:]
                    window_states = window_states[-max_points:]

                # Send command to MCU2
                combined_command = f"{command1};{command2}"
                mcu2_socket.sendall(combined_command.encode())
                print(f"Sent to MCU2: {combined_command}")

                # Get acknowledgment
                ack = mcu2_socket.recv(BUFF_SIZE).decode()
                print('MCU2 Response: ' + ack)

                # Update the real-time plot
                update_plot()

            except Exception as e:
                print(f"Error processing data: {e}")

except KeyboardInterrupt:
    print("\nServer shutting down...")
finally:
    mcu1_socket.close()
    mcu2_socket.close()
    socket_mcu1.close()
    socket_mcu2.close()
    plt.close('all')