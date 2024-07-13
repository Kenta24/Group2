import cv2
import numpy as np
import time
from pythonosc import udp_client

class ImageToSound:
    def __init__(self, ip="10.103.103.47", start_port=8000):
        self.ip = ip
        self.start_port = start_port
        self.current_port = start_port
        self.client = udp_client.SimpleUDPClient(ip, start_port)
        self.previous_image = None
        self.previous_time = time.time()

    def _calculate_parameters(self, contour, gray_image):
        length = cv2.arcLength(contour, True)
        frequency = 300000 /(1.2 * length)

        current_time = time.time()
        duration = (current_time - self.previous_time)*3
        duration = int(duration)
        self.previous_time = current_time
        brightness_factor = 100000*np.mean(gray_image) / 2550.0
        thickness_factor = cv2.contourArea(contour) / length
        angles = cv2.approxPolyDP(contour, 0.04 * length, True)
        harmonics = len(angles)
        volume = (((thickness_factor + length + brightness_factor)* 10)**5) % 90 + 30

        return {
            "frequency": frequency,
            "duration": duration,
            "brightness": brightness_factor,
            "thickness": thickness_factor,
            "harmonics": harmonics,
            "volume": volume,
        }

    def _send_osc_messages(self, parameters):
        values = [
            parameters["frequency"],
            parameters["duration"],
            parameters["brightness"],
            parameters["thickness"],
            parameters["harmonics"],
            parameters["volume"]
        ]
        self.client.send_message("/sound/parameters", values)

    def _send_zero_parameters_to_all_ports(self):
        zero_parameters = {
            "frequency": 0,
            "duration": 0,
            "brightness": 0,
            "thickness": 0,
            "harmonics": 0,
            "volume": 0,
        }
        for port in range(self.start_port, self.start_port + 21):
            self.client = udp_client.SimpleUDPClient(self.ip, port)
            self._send_osc_messages(zero_parameters)

    def process_new_image(self, image_path):
        try:
            new_image = cv2.imread(image_path)
            gray_image = cv2.cvtColor(new_image, cv2.COLOR_BGR2GRAY)
        except Exception as e:
            print(f"Failed to load image: {e}")
            return None

        if self.previous_image is None:
            self.previous_image = gray_image
            self.previous_time = time.time()
            
            diff_image = gray_image
            _, thresh = cv2.threshold(diff_image, 25, 255, cv2.THRESH_BINARY)
            contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            if contours:
                largest_contour = max(contours, key=cv2.contourArea)
                parameters = self._calculate_parameters(largest_contour, gray_image)
                self._send_osc_messages(parameters)
                return parameters
            return None

        diff_image = cv2.absdiff(self.previous_image, gray_image)
        _, thresh = cv2.threshold(diff_image, 25, 255, cv2.THRESH_BINARY)
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        if contours:
            largest_contour = max(contours, key=cv2.contourArea)
            parameters = self._calculate_parameters(largest_contour, gray_image)
            self._send_osc_messages(parameters)
            self.current_port += 1
            if self.current_port > self.start_port + 20:
                self.current_port = self.start_port
            self.client = udp_client.SimpleUDPClient(self.ip, self.current_port)
            self.previous_image = gray_image
            return parameters

        self.previous_image = gray_image
        return None

    def reset_ports_and_send_zero(self):
        self.current_port = self.start_port
        self._send_zero_parameters_to_all_ports()
