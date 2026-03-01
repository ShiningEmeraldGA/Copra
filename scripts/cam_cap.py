import subprocess
import time
import sys
import termios
import tty

def start_stream():
    return subprocess.Popen([
        "libcamera-vid",
        "-t", "0",
        "--preview",
        "--framerate", "30",
        "--width", "640", "--height", "480"
    ])

def capture_image(stream_proc):
    print("⏸️ Stopping stream to capture image...")
    stream_proc.terminate()
    stream_proc.wait()

    timestamp = time.strftime("%Y%m%d-%H%M%S")
    subprocess.run([
        "libcamera-still",
        "-o", f"capture_{timestamp}.jpg",
        "--nopreview",
        "-t", "1"
    ])

    print("▶️ Restarting stream...")
    return start_stream()


def get_char():
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setcbreak(fd)
        ch = sys.stdin.read(1)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    return ch

def main():
    print("Starting video stream...")
    stream_proc = start_stream()

    print("Press [C] to capture, [Q] to quit.")
    try:
        while True:
            ch = get_char().lower()
            if ch == 'c':
                print("📸 Snap!")
                stream_proc = capture_image(stream_proc)
            elif ch == 'q':
                print("👋 Quitting.")
                break
    finally:
        stream_proc.terminate()
        stream_proc.wait()

if __name__ == "__main__":
    main()
