"""
Meeting Assistant for Google Meet using Azure Speech Service

Features:
- Monitors running windows to detect if a Google Meet meeting is active.
- Automatically starts continuous transcription when a meeting is detected.
- Provides Pause/Resume buttons.
- Keeps a transcript that persists after the meeting ends.
- Offers Copy-to-Clipboard and Download (save to file) options.
- (Simulated) speaker labels are alternated for each recognized phrase.

Before running:
1. Install dependencies:
   pip install pyqt5 azure-cognitiveservices-speech pywin32

2. In Windows, configure your default recording device (or use a virtual audio cable)
   so that Google Meet’s audio is captured (e.g. enable “Stereo Mix”).

3. Replace "YourAzureSubscriptionKey" and "YourRegion" with your Azure Speech Service credentials.
"""

import sys
import time
import azure.cognitiveservices.speech as speechsdk
from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow,
    QTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
    QFileDialog,
    QMessageBox,
    QLabel,
)
from PyQt5.QtCore import QTimer, Qt
import win32gui

# -------------------------
# Utility function to check for a Google Meet window.
# This function enumerates all top-level windows and returns True
# if any visible window has "Meet" in its title.
# (You might want to adjust the keyword as needed.)
# -------------------------
def check_for_google_meet():
    meet_found = False

    def enum_window(hwnd, lParam):
        nonlocal meet_found
        if win32gui.IsWindowVisible(hwnd):
            title = win32gui.GetWindowText(hwnd)
            # A very simple check: if "Meet" is anywhere in the window title.
            if "Meet" in title:
                meet_found = True

    win32gui.EnumWindows(enum_window, None)
    return meet_found


# -------------------------
# Main Application Window
# -------------------------
class MeetingAssistantApp(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Meeting Assistant")
        self.resize(600, 500)

        # Transcript text will be stored here.
        self.transcript_text = ""
        # A simple toggle to simulate speaker detection (alternate speakers)
        self.speaker_toggle = True

        # Flags to track transcription state.
        self.transcribing = False
        self.paused = False

        # Build the GUI.
        self.setup_ui()

        # Initialize Azure Speech Service recognizer.
        self.setup_speech_recognizer()

        # Timer to check for an active Google Meet meeting every 5 seconds.
        self.meet_check_timer = QTimer()
        self.meet_check_timer.timeout.connect(self.auto_start_if_meet_detected)
        self.meet_check_timer.start(5000)

    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        layout = QVBoxLayout()

        self.status_label = QLabel("Status: Waiting for meeting ...")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_label)

        # Text edit to display transcript.
        self.transcript_edit = QTextEdit()
        self.transcript_edit.setReadOnly(True)
        layout.addWidget(self.transcript_edit)

        # Control buttons.
        self.start_button = QPushButton("Start Transcription")
        self.start_button.clicked.connect(self.start_transcription)
        layout.addWidget(self.start_button)

        self.pause_button = QPushButton("Pause Transcription")
        self.pause_button.clicked.connect(self.toggle_pause_resume)
        self.pause_button.setEnabled(False)
        layout.addWidget(self.pause_button)

        self.copy_button = QPushButton("Copy Transcript")
        self.copy_button.clicked.connect(self.copy_transcript)
        layout.addWidget(self.copy_button)

        self.download_button = QPushButton("Download Transcript")
        self.download_button.clicked.connect(self.download_transcript)
        layout.addWidget(self.download_button)

        central_widget.setLayout(layout)

    def setup_speech_recognizer(self):
        # Replace these with your Azure Speech Service credentials.
        subscription_key = "YourAzureSubscriptionKey"
        region = "YourRegion"

        self.speech_config = speechsdk.SpeechConfig(
            subscription=subscription_key, region=region
        )
        # Set language if needed (default is en-US)
        self.speech_config.speech_recognition_language = "en-US"

        # Use the default microphone. For capturing system audio,
        # configure Windows to use "Stereo Mix" (or similar) as the default recording device.
        self.audio_config = speechsdk.audio.AudioConfig(use_default_microphone=True)

        # Create the recognizer.
        self.recognizer = speechsdk.SpeechRecognizer(
            speech_config=self.speech_config, audio_config=self.audio_config
        )

        # Connect event handlers.
        self.recognizer.recognizing.connect(self.on_recognizing)
        self.recognizer.recognized.connect(self.on_recognized)
        self.recognizer.session_started.connect(self.on_session_started)
        self.recognizer.session_stopped.connect(self.on_session_stopped)
        self.recognizer.canceled.connect(self.on_canceled)

    # -------------------------
    # Event Handlers for Azure Speech SDK
    # -------------------------
    def on_recognizing(self, evt):
        # evt.result.text contains the partially recognized text.
        # We update the status label with the in-progress text.
        partial = evt.result.text
        self.status_label.setText(f"Recognizing: {partial}")

    def on_recognized(self, evt):
        # evt.result.text contains the final recognized text.
        result_text = evt.result.text.strip()
        if result_text:
            # Here we simulate speaker identification by alternating labels.
            speaker_label = "Speaker 1" if self.speaker_toggle else "Speaker 2"
            self.speaker_toggle = not self.speaker_toggle

            new_line = f"{speaker_label}: {result_text}\n"
            self.transcript_text += new_line
            self.transcript_edit.append(new_line)
        self.status_label.setText("Listening...")

    def on_session_started(self, evt):
        self.transcribing = True
        self.status_label.setText("Transcription started.")
        self.pause_button.setEnabled(True)
        print("Session started.")

    def on_session_stopped(self, evt):
        self.transcribing = False
        self.status_label.setText("Transcription stopped.")
        self.pause_button.setEnabled(False)
        print("Session stopped.")

    def on_canceled(self, evt):
        self.transcribing = False
        self.status_label.setText("Transcription canceled.")
        self.pause_button.setEnabled(False)
        print("Canceled: {}".format(evt))

    # -------------------------
    # Methods for Transcription Control
    # -------------------------
    def start_transcription(self):
        if not self.transcribing:
            try:
                self.recognizer.start_continuous_recognition_async()
                self.status_label.setText("Starting transcription...")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to start transcription: {e}")
        else:
            QMessageBox.information(self, "Info", "Transcription is already running.")

    def stop_transcription(self):
        if self.transcribing:
            try:
                self.recognizer.stop_continuous_recognition_async()
                self.status_label.setText("Stopping transcription...")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to stop transcription: {e}")

    def toggle_pause_resume(self):
        # We “pause” by stopping continuous recognition and “resume” by restarting it.
        if self.transcribing and not self.paused:
            self.stop_transcription()
            self.paused = True
            self.pause_button.setText("Resume Transcription")
            self.status_label.setText("Transcription paused.")
        elif self.paused:
            self.start_transcription()
            self.paused = False
            self.pause_button.setText("Pause Transcription")
            self.status_label.setText("Resumed transcription.")

    # -------------------------
    # Methods for Transcript Copy/Download
    # -------------------------
    def copy_transcript(self):
        clipboard = QApplication.clipboard()
        clipboard.setText(self.transcript_text)
        QMessageBox.information(self, "Copied", "Transcript copied to clipboard.")

    def download_transcript(self):
        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Transcript",
            f"transcript_{int(time.time())}.txt",
            "Text Files (*.txt);;All Files (*)",
            options=options,
        )
        if file_path:
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(self.transcript_text)
                QMessageBox.information(self, "Saved", "Transcript saved successfully.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to save transcript: {e}")

    # -------------------------
    # Automatic Meeting Detection
    # -------------------------
    def auto_start_if_meet_detected(self):
        # This method is called periodically to check for a Google Meet window.
        if check_for_google_meet():
            if not self.transcribing and not self.paused:
                print("Google Meet detected. Starting transcription automatically.")
                self.start_transcription()
        else:
            # Optionally, if you wish to auto-stop when the meeting ends, you can do so:
            if self.transcribing:
                print("Google Meet not detected. (Auto-stop not enabled – transcript is preserved.)")
                # Uncomment the next line to auto-stop transcription when no meeting is found.
                # self.stop_transcription()


# -------------------------
# Main Execution
# -------------------------
def main():
    app = QApplication(sys.argv)
    window = MeetingAssistantApp()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
