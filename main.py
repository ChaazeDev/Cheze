import sounddevice as sd
from pydub import AudioSegment
from tkinter import messagebox, filedialog
import numpy as np
import threading
import json
import customtkinter as tk
import sys
import logging
from logging.handlers import RotatingFileHandler

# Configure logging
log_file = "latest_log.txt"
logging.basicConfig(
    level=logging.INFO,  # Set the logging level (INFO, DEBUG, ERROR, etc.)
    format="%(asctime)s - %(levelname)s - %(message)s",  # Log format
    handlers=[
        RotatingFileHandler(log_file, maxBytes=1024 * 1024, backupCount=5),  # Keep 5 latest logs, each up to 1MB
    ]
)

# Suppress logs from the pynput library
logging.getLogger("pynput").setLevel(logging.CRITICAL)

# Redirect stdout and stderr to the logging system
class LoggingRedirector:
    def write(self, message):
        if message.strip():  # Avoid logging empty lines
            logging.info(message.strip())

    def flush(self):
        pass  # No need to flush for logging

sys.stdout = LoggingRedirector()
sys.stderr = LoggingRedirector()

DATA_TYPE = "float32"
CHUNK_SIZE = 1024  # Number of frames per chunk
sound_button_pairing = []  # List to store sound button pairs


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
            channels = sound_data["channels"]
            volume = sound_data["volume"]
            speed = sound_data.get("speed", 1.0)  # Default to normal speed (1.0x)

            # Load the sound into memory
            self.sounds[sound_name]["data"] = load_mp3_file_into_memory(path, 48000, channels, volume, speed)
        logging.info("Sounds loaded into memory.")

    def reload_config(self):
        """
        Reload the configuration and update sounds in real-time.
        """
        with self.lock:
            logging.info("Reloading configuration...")
            for child in soundList.winfo_children():
                child.destroy()
            sound_button_pairing.clear()  # Clear the list of sound button pairs
            self.load_config()
            self.load_sounds_into_memory()
            populate_sound_list()
            logging.info("Configuration reloaded.")

    def play_sound(self, sound_name):
        """
        Play a sound on all configured devices with independent volume control.
        """
        if sound_name not in self.sounds:
            logging.info(f"Sound '{sound_name}' not found in configuration.")
            return

        # Get the preloaded audio data
        original_audio_data = self.sounds[sound_name]["data"]

        for device in self.devices:
            # Get the device-specific volume
            device_volume = device.get("volume", 1.0)  # Default to 1.0 (100% volume)

            # Create a copy of the audio data for each device
            audio_data = np.copy(original_audio_data)

            # Apply volume adjustment for the device
            if device_volume > 0:
                volume_db = 20 * np.log10(device_volume)  # Convert linear volume to dB
                logging.info(f"Adjusting volume by {volume_db:.2f} dB for device {device['id']}")
                audio_data = audio_data * device_volume  # Scale the audio data
            else:
                logging.info(f"Volume is set to 0 for device {device['id']}, muting audio.")
                audio_data = audio_data * 0  # Mute the audio completely

            # Debugging: Print device-specific information
            logging.info(f"Playing sound '{sound_name}' on device {device['id']} with samplerate {device['samplerate']} and channels {device['channels']}.")

            # Create and start the output stream for the device
            stream = create_running_output_stream(device["id"], device["samplerate"], device["channels"])
            with self.lock:
                self.active_streams.append(stream)  # Track the active stream
            thread = threading.Thread(target=play_audio_on_stream, args=(audio_data, stream))
            thread.start()
                
    def stop_all_sounds(self):
        """
        Stop all active sounds and clear the active streams list.
        """
        logging.info("Stopping all sounds...")
        with self.lock:
            for stream in self.active_streams:
                try:
                    stream.abort()  # Stop the stream immediately
                    stream.close()  # Close the streamf
                except Exception as e:
                    logging.info(f"Error stopping stream: {e}")
            self.active_streams.clear()  # Clear the list of active streams

def select_sound(key):
    """
    Select a sound from the list and update the volume slider and label.
    """
    global fileName, volumeSlider, current_key

    # Get the sound data using the key
    sound_data = audio_manager.sounds.get(key)
    if not sound_data:
        messagebox.showerror("Error", f"Sound with key '{key}' not found.")
        return

    # Update the current key
    current_key = key

    # Update the sound name label using the "name" field
    fileName.configure(text=sound_data["name"])

    # Update the volume slider
    volumeSlider.delete(0, tk.END)
    volumeSlider.insert(0, sound_data["volume"] * 100)  # Set the volume slider to the current volume

def add_sound():
    """
    Add a new sound to the soundboard and update the configuration file.
    """
    global fileName, volumeSlider

    # Open a file dialog to select an MP3 file
    sound_path = filedialog.askopenfilename(filetypes=[("MP3 files", "*.mp3")])

    if sound_path:
        # Validate the file format using ffmpeg
        try:
            audio = AudioSegment.from_file(sound_path, format="mp3")
        except Exception as e:
            messagebox.showerror("Invalid File", f"Error loading file: {e}\nPlease select a valid MP3 file.")
            return

        # Create a new sound entry in the configuration
        sound_name = sound_path.split("/")[-1].split(".")[0]  # Use the filename without extension as the name
        new_sound = {
            "name": sound_name,
            "path": sound_path,
            "samplerate": 48000,  # Default sample rate
            "channels": 2,  # Default number of channels (stereo)
            "volume": 1.0,  # Default volume (100%)
            "speed": 1.0  # Default speed (1x)
        }

        # Update the configuration file
        with open("config.json", "r+") as f:
            config = json.load(f)
            config["sounds"][sound_name] = new_sound  # Add the new sound to the "sounds" dictionary
            f.seek(0)  # Move the cursor to the beginning of the file
            json.dump(config, f, indent=4)  # Write the updated config back to the file
            f.truncate()  # Ensure the file is properly truncated

        # Reload sounds into memory
        audio_manager.reload_config()

        # Update UI elements
        fileName.configure(text=sound_name)
        volumeSlider.delete(0, tk.END)
        volumeSlider.insert(0, new_sound["volume"] * 100)  # Set the vol8ume slider to the current volume

def change_keybind(current_key):
    """
    Change the keybind for the selected sound without a popup window.
    """
    if current_key == "none selected":
        messagebox.showerror("Error", "No sound selected to change keybind.")
        return

    # Change the button text to indicate key capture mode
    change_keybind_button.configure(text="Press a Key")

    def on_key_press(event):
        """
        Handle key press to set the new keybind.
        """
        # Use event.keycode to differentiate between keys
        keycode_to_key = {
            96: "KP_0", 97: "KP_1", 98: "KP_2", 99: "KP_3", 100: "KP_4",
            101: "KP_5", 102: "KP_6", 103: "KP_7", 104: "KP_8", 105: "KP_9",
            110: "KP_Decimal", 107: "KP_Add", 109: "KP_Subtract",
            106: "KP_Multiply", 111: "KP_Divide"
        }

        # Check if the keycode corresponds to a Numpad key
        new_key = keycode_to_key.get(event.keycode, event.keysym)  # Default to keysym if not a Numpad key

        try:
            # Update the configuration
            with open("config.json", "r+") as f:
                config = json.load(f)
                if current_key in config["sounds"]:
                    # Move the sound data to the new key
                    sound_data = config["sounds"].pop(current_key)
                    config["sounds"][new_key] = sound_data

                    # Save the updated configuration
                    f.seek(0)
                    json.dump(config, f, indent=4)
                    f.truncate()
                    messagebox.showinfo("Success", f"Keybind for '{sound_data['name']}' changed to '{new_key}'.")
                else:
                    messagebox.showerror("Error", f"Sound with key '{current_key}' not found in configuration.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to update keybind: {e}")
        finally:
            # Revert the button text back to "Change Keybind"
            change_keybind_button.configure(text="Change Keybind")
            # Unbind the key press event
            root.unbind("<KeyPress>")
            audio_manager.reload_config()  # Reload the configuration to reflect changes

    # Bind the key press event to the root window
    root.bind("<KeyPress>", on_key_press)

def unbind_key(current_key):
    """
    Unbind the key for the selected sound by setting its key to "unbound", "unbound1", etc.
    """
    if current_key == "none selected":
        messagebox.showerror("Error", "No sound selected to unbind.")
        return

    try:
        # Update the configuration
        with open("config.json", "r+") as f:
            config = json.load(f)
            if current_key in config["sounds"]:
                # Generate a new unbound key
                base_unbound_key = "unbound"
                unbound_key = base_unbound_key
                counter = 1
                while unbound_key in config["sounds"]:
                    unbound_key = f"{base_unbound_key}{counter}"
                    counter += 1

                # Move the sound data to the new unbound key
                sound_data = config["sounds"].pop(current_key)
                config["sounds"][unbound_key] = sound_data

                # Save the updated configuration
                f.seek(0)
                json.dump(config, f, indent=4)
                f.truncate()
                audio_manager.reload_config()  # Reload the configuration to reflect changes
                messagebox.showinfo("Success", f"Keybind for '{sound_data['name']}' has been unbound and set to '{unbound_key}'.")
            else:
                messagebox.showerror("Error", f"Key '{current_key}' not found in configuration.")
    except Exception as e:
        messagebox.showerror("Error", f"Failed to unbind key: {e}")

def load_mp3_file_into_memory(path, target_sample_rate, channels, volume, speed=1.0):
    """
    Load an MP3 file into memory as a NumPy array with the correct sample rate, number of channels, and volume.
    Always resample to 48000 Hz for consistent playback, with speed as a logical multiplier (e.g., 1.5 = 1.5x playback speed).
    """
    DEFAULT_SAMPLE_RATE = 48000  # Enforce 48000 Hz playback sample rate

    # Load the audio file
    audio = AudioSegment.from_file(path, format="mp3")

    # Adjust the sample rate based on the speed multiplier
    adjusted_sample_rate = int(DEFAULT_SAMPLE_RATE / speed)  # Divide by speed for faster playback
    logging.info(f"Adjusting playback speed for {path}: {speed}x (Sample rate: {adjusted_sample_rate} Hz)")
    audio = audio.set_frame_rate(adjusted_sample_rate)

    # Convert to the correct number of channels
    if audio.channels != channels:
        logging.info(f"Converting {path} to {channels} channels")
        audio = audio.set_channels(channels)

    # Apply volume adjustment (convert linear volume to dB)
    if volume > 0:
        volume_db = 20 * np.log10(volume)  # Convert linear volume to dB
        logging.info(f"Adjusting volume by {volume_db:.2f} dB for {path}")
        audio = audio + volume_db
    else:
        logging.info(f"Volume is set to 0 for {path}, muting audio.")
        audio = audio - 120  # Mute the audio completely

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
        logging.info(f"Error during playback: {e}")

def populate_sound_list():
    """
    Populate the soundList with buttons for each sound in the configuration.
    """
    for key, sound_data in audio_manager.sounds.items():
        sound_button = tk.CTkButton(
            master=soundList,
            height=30,
            width=600,
            corner_radius=10,
            fg_color="#212121",
            hover_color="#1a1a1a",
            text=sound_data["name"],  # Display the sound's name
            command=lambda k=key: select_sound(k)  # Pass the key to select_sound
        )
        sound_button.pack(padx=5, pady=1, fill="x")
        sound_button_pairing.append((sound_button, sound_data))

def play_selected_sound(key):
    """
    Play the currently selected sound.
    """
    if key == "none selected":
        messagebox.showerror("Error", "No sound selected to play.")
        return

    if key in audio_manager.sounds:
        audio_manager.play_sound(key)
    else:
        messagebox.showerror("Error", f"Sound with key '{key}' not found.")

def apply_volume_change(event=None):
    """
    Apply the volume change for the currently selected sound.
    """
    global current_key

    if current_key == "none selected":
        messagebox.showerror("Error", "No sound selected to change volume.")
        return

    try:
        # Get the new volume value from the slider
        new_volume = float(volumeSlider.get()) / 100  # Convert percentage to a float between 0 and 1

        # Update the volume in the audio_manager and config.json
        if current_key in audio_manager.sounds:
            audio_manager.sounds[current_key]["volume"] = new_volume

            # Update the configuration file
            with open("config.json", "r+") as f:
                config = json.load(f)
                config["sounds"][current_key]["volume"] = new_volume
                f.seek(0)
                json.dump(config, f, indent=4)
                f.truncate()

            messagebox.showinfo("Success", f"Volume for '{audio_manager.sounds[current_key]['name']}' updated to {new_volume * 100:.0f}%.")
        else:
            messagebox.showerror("Error", f"Sound with key '{current_key}' not found.")
    except ValueError:
        messagebox.showerror("Error", "Invalid volume value. Please enter a number between 0 and 100.")

if __name__ == "__main__":
    import pynput
    
    root = tk.CTk()
    root.geometry("640x480")
    root.title("Cheze soundboard")
 
    volume = tk.StringVar()
    pitch = tk.StringVar()
    speed = tk.StringVar()
 
    open_button = tk.CTkButton(root, text="Add audio file", command=lambda: add_sound())
    open_button.pack(padx=20, pady=20)
 
    Title = tk.CTkLabel(root, text="Cheze custom soundboard", font=("Roboto", 20))
    Title.pack()
 
    OutputConfig = tk.CTkFrame(root, height=50, width=1920, fg_color="#1a1a1a")
    OutputConfig.pack(side="bottom", fill="x")

    settingsFrame = tk.CTkFrame(master=root, width=200, height=200)
    settingsFrame.pack(side="right", fill="y")
 
    tk.CTkLabel(master=settingsFrame, text="name: ").grid(row=0, column=0, padx=20)
    fileName = tk.CTkLabel(master=settingsFrame, text="none selected",
                         wraplength=100)
    fileName.grid(row=0,column=1, columnspan=10, sticky="w")
 
    tk.CTkLabel(master=settingsFrame, text="volume:").grid(row=1, column=0, padx=20)
    volumeSlider = tk.CTkEntry(master=settingsFrame, width=100, textvariable=volume)
    volumeSlider.grid(row=1, column=1)
    tk.CTkLabel(master=settingsFrame, text="%").grid(row=1, column=2, padx=10)

    volumeSlider.bind("<Return>", apply_volume_change)  # Apply volume change on Enter key press
    volumeSlider.bind("<FocusOut>", apply_volume_change)  # Apply volume change when input loses focus

    # Add a "Change Keybind" button
    change_keybind_button = tk.CTkButton(
        master=settingsFrame,
        text="Change Keybind",
        command=lambda: change_keybind(current_key)  # Use current_key
    )
    change_keybind_button.grid(row=2, column=0, columnspan=3, pady=10)

    # Add the "Unbind Key" button
    unbind_key_button = tk.CTkButton(
        master=settingsFrame,
        text="Unbind Key",
        command=lambda: unbind_key(current_key)  # Use current_key
    )
    unbind_key_button.grid(row=3, column=0, columnspan=3, pady=10)

    # Add the "Play Sound" button
    play_sound_button = tk.CTkButton(
        master=settingsFrame,
        text="Play Sound",
        command=lambda: play_selected_sound(current_key)  # Use current_key
    )
    play_sound_button.grid(row=4, column=0, columnspan=3, pady=10)

    # Add the "Apply Volume Change" button
    apply_volume_button = tk.CTkButton(
        master=settingsFrame,
        text="Apply Volume Change",
        command=apply_volume_change
    )
    apply_volume_button.grid(row=5, column=0, columnspan=3, pady=10)
 
    soundList = tk.CTkScrollableFrame(master=root, height=300, width=4000)
    soundList.pack(fill="both", side="left")
    
    # Initialize the AudioManager with a configuration file
    audio_manager = AudioManager("config.json")
    populate_sound_list()

    def on_press(key):
        """
        Handle key press events.
        """
        # Map virtual keycodes to descriptive key names for Numpad keys
        keycode_to_key = {
            96: "KP_0", 97: "KP_1", 98: "KP_2", 99: "KP_3", 100: "KP_4",
            101: "KP_5", 102: "KP_6", 103: "KP_7", 104: "KP_8", 105: "KP_9",
            110: "KP_Decimal", 107: "KP_Add", 109: "KP_Subtract",
            106: "KP_Multiply", 111: "KP_Divide"
        }

        try:
            # Check if the key has a virtual keycode
            if hasattr(key, "vk"):
                # Map the virtual keycode to a key name (e.g., "KP_5" for Numpad 5)
                key_name = keycode_to_key.get(key.vk, key.char if hasattr(key, "char") else str(key.vk))

                # Check if the key is configured in the sounds dictionary
                if key_name in audio_manager.sounds:
                    # Play the sound associated with the key
                    audio_manager.play_sound(key_name)
                elif key.vk == 110:  # Numpad . (period)
                    audio_manager.stop_all_sounds()
        except AttributeError:
            logging.info(f"Key '{key}' does not have a valid char or vk attribute.")
        except Exception as e:
            logging.error(f"Error handling key press: {e}")

    def start_keyboard_listener():
        """
        Start the pynput keyboard listener in a separate thread.
        """
        logging.info("Press a configured key to play a sound. Press Numpad . to stop all sounds.")
        with pynput.keyboard.Listener(on_press=on_press) as listener:
            listener.join()

    # Start the keyboard listener in a separate thread
    keyboard_thread = threading.Thread(target=start_keyboard_listener, daemon=True)
    keyboard_thread.start()

    # Start the tkinter main loop
    root.mainloop()