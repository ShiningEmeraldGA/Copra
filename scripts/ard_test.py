import serial
import time

# Adjust this depending on your port (often /dev/ttyUSB0 or /dev/ttyACM0)
arduino = serial.Serial('/dev/ttyACM0', 9600)
time.sleep(2)  # Wait for Arduino to reset

def send_command(cmd):
    arduino.write((cmd + '\n').encode())
    print(f"Sent: {cmd}")

# Example usage
send_command("ON")
time.sleep(2)
send_command("OFF")

arduino.close()
