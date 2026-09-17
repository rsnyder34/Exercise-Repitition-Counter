from parse import parse_mpu6050

PORT = "COM3"
BAUDRATE = 115200

if __name__ == "__main__":
    for data in parse_mpu6050(PORT,BAUDRATE):
        print(f"Parsed data: {data}")