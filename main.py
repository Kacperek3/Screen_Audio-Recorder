import cv2
import pyautogui
import pyaudio
import numpy as np
import wave
from multiprocessing import Process, Event
from moviepy.editor import VideoFileClip, AudioFileClip
from PyQt5.QtWidgets import QApplication, QMainWindow, QTimeEdit
from PyQt5 import uic
import time
from PyQt5.QtCore import QTime, QTimer

audio_output_file = 'audio_recording.wav'
frames = []
stream = None

def voice_recording(stop_event):
    chunk_size = 1024
    sample_format = pyaudio.paInt16
    channels = 1
    sample_rate = 44100

    # Inicjalizacja PyAudio
    pa = pyaudio.PyAudio()

    stream = pa.open(format=sample_format,
                     channels=channels,
                     rate=sample_rate,
                     input=True,
                     frames_per_buffer=chunk_size)

    try:
        while not stop_event.is_set():
            data = stream.read(chunk_size)
            frames.append(data)
    except KeyboardInterrupt:
        pass
    finally:
        stream.stop_stream()
        stream.close()
        pa.terminate()

    with wave.open(audio_output_file, 'wb') as wav_file:
        wav_file.setnchannels(channels)
        wav_file.setsampwidth(pa.get_sample_size(sample_format))
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(b''.join(frames))


output_file = 'screen_recording.mp4'

def recording(stop_event):
    fps = 20.0
    resolution = (1920, 1080)

    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_file, fourcc, fps, resolution)

    try:
        while not stop_event.is_set():
            img = pyautogui.screenshot(region=(0, 0, resolution[0], resolution[1]))
            frame = np.array(img)
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            out.write(frame)
    finally:
        cv2.destroyAllWindows()
        out.release()

def merge_video_audio(video_file, audio_file, output_file):
    video = VideoFileClip(video_file)
    audio = AudioFileClip(audio_file)

    # Ustalanie długości nagrania dźwiękowego na podstawie długości nagrania wideo
    video = video.subclip(0, audio.duration)

    # Połączenie wideo i dźwięku
    video = video.set_audio(audio)

    # Zapisanie połączonego pliku wideo
    video.write_videofile(output_file, codec="libx264", audio_codec="aac")

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setFixedSize(428, 181)
        self.clicked_stop = True
        uic.loadUi("screen.ui", self)
        self.checkBox.setEnabled(False)
        self.timeEdit.setDisplayFormat("hh:mm:ss")
        self.timer = QTimer()
        self.timer.start(1000)
        self.elapsed_time = QTime(0, 0, 0)
        self.timer.timeout.connect(self.update_time)
        self.pushButton.clicked.connect(self.start)
        self.pushButton_2.clicked.connect(self.stop)
        self.stop_event = Event()


    def start(self):
        self.clicked_stop = False
        self.checkBox.setChecked(True)
        self.voice_process = Process(target=voice_recording, args=(self.stop_event,))
        self.recording_process = Process(target=recording, args=(self.stop_event,))
        self.voice_process.start()
        self.recording_process.start()

    def stop(self):
        self.clicked_stop = True
        self.elapsed_time = QTime(0, 0, 0)  # Reset the elapsed time to 0
        self.timeEdit.setTime(self.elapsed_time)  # Update the QTimeEdit with the reset time
        self.checkBox.setChecked(False)
        self.stop_event.set()
        self.voice_process.join()
        self.recording_process.join()
        final = self.textEdit.toPlainText() + ".mp4"
        merge_video_audio(output_file, audio_output_file, final)

    def update_time(self):
        if not self.clicked_stop:
            self.elapsed_time = self.elapsed_time.addSecs(1)
            self.timeEdit.setTime(self.elapsed_time)

if __name__ == "__main__":
    app = QApplication([])
    window = MainWindow()
    window.show()
    app.exec_()
