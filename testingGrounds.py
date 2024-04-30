import customtkinter as tk
from tkinter import messagebox
from tkinter import filedialog
import pygame._sdl2.audio as sdl2_audio
from pygame import mixer
import json
from pynput import keyboard
from threading import Thread

selected_sound=None




def playOnMic(sound):
	print("eyy lmao")


def on_press(key):
	if str(key) == stopKey:
		STOP_THE_PAIN()
		return

	for sound in settings:
		if not sound == "global":
			if settings[sound]['Hotkey'] == str(key):

				if settings[sound]["cancelOther"] == "1":
					cancelOther = True
				else:
					cancelOther = False

				for double in playable_sounds:
					if double[0] == sound.split("/")[len(sound.split("/"))-1]:
						double[1].set_volume(float(settings[sound]["volume"])/100)
						double[1].play()
						playMic = Thread(target=playOnMic, args=(double[1],))
						playMic.start()
					elif cancelOther == True:
						double[1].stop()
						
					
def STOP_THE_PAIN():
	for double in playable_sounds:		
		double[1].stop()
					
			

def open_file_dialog():
    global file_path
    global sound
    file_path = filedialog.askopenfilename(title="Select a File", filetypes=[("Audio files", "*.mp3 *.ogg")])
    if file_path:
        for sound in soundList.winfo_children():
            if sound.cget("text") == file_path.split("/")[len(file_path.split("/"))-1]:
                sound.destroy()

        soundLabel = tk.CTkButton(master=soundList, height=30, width=600, corner_radius=10,  fg_color="#212121", hover_color="#1a1a1a", text=F"{file_path.split("/")[len(file_path.split("/"))-1]}",
								  command=lambda:select_sound(file_path))
        soundLabel.pack(fill="x", padx=5, pady=1)
		
        if volume.get() == '':
            Svolume = 100
        else:
            Svolume= float(volume.get())

        settings[file_path] = {
                "Hotkey": "Null and Void",
                "volume":float(Svolume),
                "name": F"{file_path.split("/")[len(file_path.split("/"))-1]}",
				"cancelOther": "0"
		}
        

        
        play_audio.configure(state="normal")




def play_file_audio():
	
	try:
		global playing
		if playing == True:
			selected_sound.stop()
			play_audio.configure(text="Play audio")
			playing = False
		else:
			if not volume.get() == '':
				selected_sound.set_volume(float(volume.get())/100)
			selected_sound.play()
			play_audio.configure(text="Stop audio")
			playing = True
		error_box.configure(text="")
	except ValueError:
		error_box.configure(text="Non-number volume.")

	
def on_closing():
	if messagebox.askokcancel("Quit", "Are you sure you want to quit?"):
		global settings
		with open("settings.json", "w") as settingsFile:			
			try:
				json.dump(settings, settingsFile)
				settingsFile.close()
				root.destroy()
			except NameError:
				json.dump(settings, settingsFile)
				settingsFile.close()
				root.destroy()
			

def select_sound(sound):

	
	global selected_sound
	global selected_sound_name
	prevSound = fileName.cget("text")
	if not prevSound == "none selected" and not prevSound == "stop":
		changeVolume(1)
		changeCancel()

	if sound == "stop":
		fileName.configure(text="stop all sounds")
		volumeSlider.configure(state="disabled")
		play_audio.configure(state="disabled")
		change_keybind.configure(state="normal")
		cancel_other.configure(state="disabled")
		selected_sound_name = "stop"
		return

	fileName.configure(text=sound.split("/")[len(sound.split("/"))-1])
	for possibleSound in playable_sounds:
		if possibleSound[0] == sound:
			selected_sound_name = sound
			selected_sound = possibleSound[1]


	for sfx in settings:
		if not sfx == "global":
			
			if settings[sfx]["name"] == sound:
				volumeSlider.delete(0,9999)
				volumeSlider.insert(0, settings[sfx]["volume"])
				if settings[sfx]["cancelOther"] == "1":
					cancel_other.select()
				elif settings[sfx]["cancelOther"] == "0":
					cancel_other.deselect()
		play_audio.configure(state="normal")
		cancel_other.configure(state="normal")
		change_keybind.configure(state="normal")
		volumeSlider.configure(state="normal")


def SoundEdit(key):
	listener2.stop()
	global selected_sound_name
	global stopKey

	if selected_sound_name == 'stop':
		stopKey = str(key)
		change_keybind.configure(text="change keybind")
		settings["global"]["Stopkey"] = stopKey
		return


	for sound in settings:
		if not sound=="global": 
				if settings[sound]["name"] == selected_sound_name:
					settings[sound]["Hotkey"] = str(key)
	change_keybind.configure(text="change keybind")


def edit_sound_key():
	
	change_keybind.configure(text="press a key...")
	global listener2
	listener2 = keyboard.Listener(on_press=SoundEdit)
	listener2.start()
	
playing = False

def reconfig_audio1(choice):
	settings["global"]["audio1"] = choice

def reconfig_audio2(choice):
	settings["global"]["audio2"] = choice
	mixer.init(devicename=choice)


def initiate_program():
	global playable_sounds
	global stopKey
	with open("settings.json", "r") as settingsFile:	
		global settings
		settings = json.load(settingsFile)
		settingsFile.close()
	y=0
	mixer.init(devicename=settings["global"]["audio2"])
	list_of_sounds = []
	playable_sounds = []
	stop_all_sounds = tk.CTkButton(master=soundList, height=30, width=600, corner_radius=10,  fg_color="#212121", hover_color="#1a1a1a",  text="stop all sounds", command=lambda: select_sound("stop"))
	stop_all_sounds.pack(fill='x', padx=5, pady=1)
	for sound in settings:
		if not sound=="global":
			soundButton = tk.CTkButton(master=soundList, height=30, width=600, corner_radius=10,  fg_color="#212121", hover_color="#1a1a1a",  text=settings[sound]["name"])
			list_of_sounds.append((soundButton, settings[sound]["name"]))
			soundButton.pack(fill="x", padx=5, pady=1)
			playable_sounds.append((settings[sound]["name"], mixer.Sound(sound)))
			
			y+=1
	
	i=0
	for i in range(len(list_of_sounds)):
		list_of_sounds[i][0].configure(command=lambda i=i: select_sound(list_of_sounds[i][1]))

	audioDevices = list(sdl2_audio.get_audio_device_names())
	outputDevice1.configure(values=audioDevices)
	outputDevice2.configure(values=audioDevices)
	stopKey = settings["global"]["Stopkey"]


	try:
		outputDevice1.set(settings["global"]["audio1"])
	except:
		print("could not set audio device 1: Device not found")
	try:
		outputDevice2.set(settings["global"]["audio2"])
	except:
		print("could not set audio device 2: Device not found")

def changeVolume(x):
	global settings
	global selected_sound_name
	for sound in settings:
			if not sound == "global":
				if settings[sound]["name"] == selected_sound_name:
					settings[sound]["volume"] = float(volumeSlider.get())



def changeCancel():
	global settings
	global selected_sound_name

	for sound in settings:
		if not sound == "global":
			if settings[sound]["name"] == selected_sound_name:
				settings[sound]["cancelOther"] = str(cancel_other.get())

if __name__ == '__main__':
	root = tk.CTk()
	root.geometry("640x480")
	root.title("Cheze soundboard")

	volume = tk.StringVar()
	pitch = tk.StringVar()
	speed = tk.StringVar()

	open_button = tk.CTkButton(root, text="Add audio file", command=open_file_dialog)
	open_button.pack(padx=20, pady=20)

	Title = tk.CTkLabel(root, text="Cheze custom soundboard", font=("Roboto", 20))
	Title.pack()

	OutputConfig = tk.CTkFrame(root, height=200, width=1920, fg_color="#1a1a1a")
	OutputConfig.pack(side="bottom", fill="x")

	tk.CTkLabel(OutputConfig, text="Output device 1 (speakers)").pack(side="left", padx=10)
	outputDevice1 = tk.CTkOptionMenu(OutputConfig, values=[""], command=reconfig_audio1, dynamic_resizing=False)
	outputDevice1.pack(side="left")


	outputDevice2 = tk.CTkOptionMenu(OutputConfig, values=[""], command=reconfig_audio2,dynamic_resizing=False)
	outputDevice2.pack(side="right")
	tk.CTkLabel(OutputConfig, text="Output device 2 (VA cable)").pack(side="right", padx=10)

	settingsFrame = tk.CTkFrame(master=root, width=200, height=200)
	settingsFrame.pack(side="right", fill="y")

	tk.CTkLabel(master=settingsFrame, text="name: ").grid(row=0, column=0, padx=20)
	fileName = tk.CTkLabel(master=settingsFrame, text="none selected",
						wraplength=100)
	fileName.grid(row=0,column=1, columnspan=10, sticky="w")


	tk.CTkLabel(master=settingsFrame, text="volume:").grid(row=1, column=0, padx=20)
	volumeSlider = tk.CTkEntry(master=settingsFrame, width=100, textvariable=volume)
	volumeSlider.bind("<Return>", changeVolume)
	volumeSlider.grid(row=1, column=1)
	tk.CTkLabel(master=settingsFrame, text="%").grid(row=1, column=2, padx=10)

	change_keybind = tk.CTkButton(settingsFrame, text="Change keybind", state="disabled", command=lambda: edit_sound_key())
	change_keybind.grid(sticky="s", row=98, column=0, columnspan=10)

	play_audio = tk.CTkButton(settingsFrame, text="Play audio", state="disabled", command = lambda: play_file_audio())
	play_audio.grid(pady=10, sticky="s", row=99, column=0, columnspan=10)

	cancel_other = tk.CTkCheckBox(settingsFrame, text="Stop other sounds", state="disabled", command=changeCancel)
	cancel_other.grid(row=2, column=0, columnspan=2, pady=10)

	error_box = tk.CTkLabel(master=settingsFrame, text="", text_color="red")
	error_box.grid(row=3,column=0, columnspan=3)

	settingsFrame.grid_rowconfigure(99, weight=1)
	settingsFrame.grid_rowconfigure(98, weight=100)

	soundList = tk.CTkScrollableFrame(master=root, height=300, width=4000)
	soundList.pack(fill="both", side="left")

	root.protocol("WM_DELETE_WINDOW", on_closing)

	initiate_program()
	listener = keyboard.Listener(on_press=on_press)
	listener.start()

	root.mainloop()