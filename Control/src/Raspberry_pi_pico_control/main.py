import machine
import sys
import select

while True:
    if sys.stdin in select.select([sys.stdin], [], [], 0)[0]:
        command = sys.stdin.readline().strip()
        try:
            exec(command)
        except Exception as e:
            print(f"Error: {e}")