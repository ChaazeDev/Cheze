import sounddevice as sd
from pydub import AudioSegment
import numpy as np
import threading
import json

DATA_TYPE = "float32"
CHUNK_SIZE = 1024  # Number of frames per chunk

class AudioManager:
    def __init__(self, config_path):
        """
        Initialize the AudioManager with a configuration file.
        """
        self.config_path = config_path
        self.sounds = {}
        self.devices = []
        self.active_streams = []  # List to track active streams
        self.lock = threading.Lock()  # Lock to safely manage active streams
        self.load_config()
        self.load_sounds_into_memory()

    def load_config(self):
        """
        Load the configuration from a JSON file.
        """
        with open(self.config_path, "r") as f:
            config = json.load(f)
        self.devices = config["devices"]
        self.sounds = config["sounds"]

    def load_sounds_into_memory(self):
        """
        Load all sounds into memory for faster playback.
        """
        for sound_name, sound_data in self.sounds.items():
            path = sound_data["path"]
            target_sample_rate = sound_data["samplerate"]
            channels = sound_data["channels"]
            self.sounds[sound_name]["data"] = load_mp3_file_into_memory(path, target_sample_rate, channels)

    def play_sound(self, sound_name):
        """
        Play a sound on all configured devices.
        """
        if sound_name not in self.sounds:
            print(f"Sound '{sound_name}' not found in configuration.")
            return

        audio_data = self.sounds[sound_name]["data"]

        for device in self.devices:
            stream = create_running_output_stream(device["id"], device["samplerate"], device["channels"])
            with self.lock:
                self.active_streams.append(stream)  # Track the active stream
            thread = threading.Thread(target=play_audio_on_stream, args=(audio_data, stream))
            thread.start()

    def stop_all_sounds(self):
        """
        Stop all active sounds and clear the active streams list.
        """
        print("Stopping all sounds...")
        with self.lock:
            for stream in self.active_streams:
                try:
                    stream.abort()  # Stop the stream immediately
                    stream.close()  # Close the stream
                except Exception as e:
                    print(f"Error stopping stream: {e}")
            self.active_streams.clear()  # Clear the list of active streams

def load_mp3_file_into_memory(path, target_sample_rate, channels):
    """
    Load an MP3 file into memory as a NumPy array with the correct sample rate and number of channels.
    """
    audio = AudioSegment.from_file(path, format="mp3")
    
    # Resample to the target sample rate
    if audio.frame_rate != target_sample_rate:
        audio = audio.set_frame_rate(target_sample_rate)
    
    # Convert to the correct number of channels
    if audio.channels != channels:
        audio = audio.set_channels(channels)
    
    # Force 16-bit audio
    audio = audio.set_sample_width(2)  # 2 bytes = 16 bits
    
    # Convert to NumPy array
    raw_data = np.frombuffer(audio.raw_data, dtype=np.int16)
    
    # Reshape the data to match the number of channels
    if channels > 1:
        raw_data = raw_data.reshape((-1, channels))
    
    # Convert int16 data to float32
    raw_data = raw_data.astype(np.float32) / 32768.0  # Normalize to range [-1.0, 1.0]
    
    return raw_data

def create_running_output_stream(index, samplerate, channels):
    """
    Create a sounddevice.OutputStream for the specified device.
    """
    output = sd.OutputStream(
        device=index,
        samplerate=samplerate,
        channels=channels,
        dtype=DATA_TYPE
    )
    output.start()
    return output

def play_audio_on_stream(audio_data, stream_object):
    """
    Play audio data on a given stream in chunks.
    """
    try:
        # Write audio data in chunks to avoid stuttering
        for i in range(0, len(audio_data), CHUNK_SIZE):
            chunk = audio_data[i:i + CHUNK_SIZE]
            stream_object.write(chunk)
    except Exception as e:
        print(f"Error during playback: {e}")

if __name__ == "__main__":
    import pynput

    # Initialize the AudioManager with a configuration file
    audio_manager = AudioManager("config.json")

    def on_press(key):
        """
        Handle key press events.
        """
        try:
            if hasattr(key, "vk"):
                if str(key.vk) in audio_manager.sounds:
                    # Play the sound directly using the key's configuration
                    audio_manager.play_sound(str(key.vk))
                elif key.vk == 110:  # Numpad . (period)
                    audio_manager.stop_all_sounds()
        except Exception as e:
            print(f"Error handling key press: {e}")

    print("Press a configured key to play a sound. Press Numpad . to stop all sounds.")
    with pynput.keyboard.Listener(on_press=on_press) as listener:
        listener.join()