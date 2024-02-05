import customtkinter as tk
from tkinter import filedialog
from pygame import mixer


def open_file_dialog():
    global file_path
    global sound
    file_path = filedialog.askopenfilename(title="Select a File", filetypes=[("Audio files", "*.mp3 *.ogg"), ("All files", "*.*")])
    if file_path:
        selected_file_label.configure(text=f"Selected File:\n{file_path}")
        sound = mixer.Sound(file_path)
        play_audio.configure(state="normal")

def play_file_audio(audio):
	global playing
	if playing == True:
		sound.stop()
		play_audio.configure(text="Play audio")
		playing = False
	else:
		sound.play()
		play_audio.configure(text="Stop audio")
		playing = True
	


mixer.init()

playing = False

root = tk.CTk()
root.geometry("640x480")
root.title("File Dialog Test")

open_button = tk.CTkButton(root, text="Open File", command=open_file_dialog)
open_button.pack(padx=20, pady=20)

selected_file_label = tk.CTkLabel(root, text="Selected File:\n ")
selected_file_label.pack()

play_audio = tk.CTkButton(root, text="Play audio", state="disabled", command = lambda: play_file_audio(file_path))
play_audio.pack(pady=20)
root.mainloop()

