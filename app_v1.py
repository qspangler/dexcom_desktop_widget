import tkinter as tk
import customtkinter as ctk
from datetime import datetime
from pydexcom import Dexcom
from tkinter import font as tkfont
import tkinter.messagebox as tkmb
import json
import os
import pystray
from PIL import Image

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class BloodSugarWidget:
    def __init__(self, master):
        self.master = master
        self.master.withdraw()  # Hide the main window initially
        self.setup_system_tray()  # Set up the system tray icon
        self.login()  # Show the login window first
        self.master.protocol("WM_DELETE_WINDOW", self.minimize_widget)  # Minimize instead of close
        self.master.bind("<Escape>", lambda e: self.show_widget())  # Press Esc to show widget
        self.low_threshold = 80  # Set the low threshold to 80 mg/dL

    def login(self):
        self.login_window = ctk.CTkToplevel(self.master)
        self.login_window.title("Dexcom Login")
        self.login_window.geometry("300x220")
        self.login_window.configure(fg_color='#2C3E50')

        frame = ctk.CTkFrame(master=self.login_window, fg_color='#2C3E50')
        frame.pack(pady=20, padx=40, fill='both', expand=True)

        label = ctk.CTkLabel(master=frame, text='Dexcom Login', text_color='#ECF0F1', font=("Helvetica", 18))
        label.pack(pady=12, padx=10)

        self.user_entry = ctk.CTkEntry(master=frame, placeholder_text="Username", fg_color='#34495E', text_color='#ECF0F1')
        self.user_entry.pack(pady=(12, 0), padx=10)

        self.pass_entry = ctk.CTkEntry(master=frame, placeholder_text="Password", show="*", fg_color='#34495E', text_color='#ECF0F1')
        self.pass_entry.pack(pady=(12, 0), padx=10)

        button = ctk.CTkButton(
            master=frame,
            text='Login',
            command=self.validate_login,
            fg_color='#3498DB',
            hover_color='#2980B9',
            text_color='#FFFFFF',
            height=35,
            corner_radius=8
        )
        button.pack(pady=(20, 12), padx=10)

        self.login_window.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.login_window.grab_set()

    def on_closing(self):
        self.minimize_widget()

    def validate_login(self):
        username = self.user_entry.get()
        password = self.pass_entry.get()
        if username and password:
            self.username = username
            self.password = password
            config_file = 'dexcom_config.json'
            with open(config_file, 'w') as f:
                json.dump({'username': self.username, 'password': self.password}, f)
            self.login_window.destroy()
            self.show_main_window()
        else:
            tkmb.showerror(title="Login Failed", message="Please enter both username and password")

    def show_main_window(self):
        self.master.deiconify()  # Show the main window
        self.setup_main_window()
        self.update_value()  # Start updating blood sugar values
        self.master.lift()  # Bring the window to the front

    def setup_main_window(self):
        self.master.overrideredirect(True)
        self.master.attributes('-topmost', True)
        widget_width = 220
        widget_height = 140
        x = self.master.winfo_screenwidth() - widget_width - 10
        y = self.master.winfo_screenheight() - widget_height - 40
        self.master.geometry(f'{widget_width}x{widget_height}+{x}+{y}')

        self.canvas = tk.Canvas(self.master, bg='#2C3E50', bd=0, highlightthickness=0)
        self.canvas.place(relx=0, rely=0, relwidth=1, relheight=1)

        button_frame = tk.Frame(self.canvas, bg='#2C3E50')
        button_frame.place(x=widget_width-90, y=2, width=90, height=30)

        minimize_button = tk.Button(button_frame, text="—", command=self.minimize_widget,
                                    bg='#2C3E50', fg='#ECF0F1', font=("Arial", 12, "bold"),
                                    bd=0, highlightthickness=0, padx=5, pady=0)
        minimize_button.pack(side=tk.LEFT, padx=(0, 5))

        close_button = tk.Button(button_frame, text="×", command=self.close_app,
                                 bg='#2C3E50', fg='#ECF0F1', font=("Arial", 12, "bold"),
                                 bd=0, highlightthickness=0, padx=5, pady=0)
        close_button.pack(side=tk.LEFT)

        value_font = tkfont.Font(family="Helvetica", size=28, weight="bold")
        trend_font = tkfont.Font(family="Helvetica", size=18)
        time_font = tkfont.Font(family="Helvetica", size=10)

        self.value_label = tk.Label(self.canvas, text="Loading...", font=value_font, bg='#2C3E50', fg='#ECF0F1')
        self.value_label.place(relx=0.5, rely=0.35, anchor="center")

        self.trend_label = tk.Label(self.canvas, text="", font=trend_font, bg='#2C3E50', fg='#BDC3C7')
        self.trend_label.place(relx=0.5, rely=0.6, anchor="center")

        self.time_label = tk.Label(self.canvas, text="", font=time_font, bg='#2C3E50', fg='#95A5A6')
        self.time_label.place(relx=0.5, rely=0.85, anchor="center")

        self.canvas.bind("<Configure>", self.create_rounded_frame)
        self.master.bind("<ButtonPress-1>", self.start_move)
        self.master.bind("<ButtonRelease-1>", self.stop_move)
        self.master.bind("<B1-Motion>", self.do_move)

        self.update_id = None
        self.is_flashing = False
        self.flash_id = None

        clear_button = tk.Button(self.canvas, text="Clear Login", command=self.clear_credentials, bg='#2C3E50', fg='#ECF0F1', font=("Arial", 8), bd=0, highlightthickness=0)
        clear_button.place(x=5, y=5)

    def create_rounded_frame(self, event):
        radius = 15
        self.canvas.delete("all")
        width, height = event.width, event.height
        self.canvas.create_rectangle(0, 0, width, height, fill='#2C3E50', outline='#2C3E50', tags="background")
        self.canvas.create_arc(0, 0, radius*2, radius*2, start=90, extent=90, fill='#2C3E50', outline='#2C3E50')
        self.canvas.create_arc(width-radius*2, 0, width, radius*2, start=0, extent=90, fill='#2C3E50', outline='#2C3E50')
        self.canvas.create_arc(0, height-radius*2, radius*2, height, start=180, extent=90, fill='#2C3E50', outline='#2C3E50')
        self.canvas.create_arc(width-radius*2, height-radius*2, width, height, start=270, extent=90, fill='#2C3E50', outline='#2C3E50')

        button_frame = tk.Frame(self.canvas, bg='#2C3E50')
        button_frame.place(x=width-90, y=2, width=90, height=30)

        minimize_button = tk.Button(button_frame, text="-", command=self.minimize_widget,
                                    bg='#2C3E50', fg='#ECF0F1', font=("Arial", 12, "bold"),
                                    bd=0, highlightthickness=0, padx=5, pady=0)
        minimize_button.pack(side=tk.LEFT, padx=(0, 5))

        close_button = tk.Button(button_frame, text="×", command=self.close_app,
                                 bg='#2C3E50', fg='#ECF0F1', font=("Arial", 12, "bold"),
                                 bd=0, highlightthickness=0, padx=5, pady=0)
        close_button.pack(side=tk.LEFT)

    def start_move(self, event):
        self.x = event.x
        self.y = event.y

    def stop_move(self, event):
        self.x = None
        self.y = None

    def do_move(self, event):
        deltax = event.x - self.x
        deltay = event.y - self.y
        x = self.master.winfo_x() + deltax
        y = self.master.winfo_y() + deltay
        self.master.geometry(f"+{x}+{y}")

    def get_blood_sugar(self):
        try:
            dexcom = Dexcom(username=self.username, password=self.password)
            glucose_reading = dexcom.get_current_glucose_reading()
            if glucose_reading:
                return {
                    "value": glucose_reading.mg_dl,
                    "trend": glucose_reading.trend_arrow,
                    "time": glucose_reading.datetime
                }
            else:
                return None
        except Exception as e:
            print(f"Error getting blood sugar: {e}")
            return None

    def update_value(self):
        try:
            blood_sugar = self.get_blood_sugar()
            if blood_sugar:
                value = blood_sugar['value']
                self.value_label.config(text=f"{value} mg/dL")
                if value < self.low_threshold:
                    color = '#E74C3C'
                    if not self.is_flashing:
                        self.is_flashing = True
                        self.flash_widget()
                    if not self.master.winfo_viewable():
                        self.show_widget()  # Show the widget if it's minimized
                elif value > 140:
                    color = '#F39C12'
                    self.stop_flashing()
                else:
                    color = '#2ECC71'
                    self.stop_flashing()
                self.value_label.config(fg=color)

                trend_arrows = {
                    "NONE": "→", "FLAT": "→", "FORTY_FIVE_UP": "↗", "SINGLE_UP": "↑",
                    "DOUBLE_UP": "⇈", "FORTY_FIVE_DOWN": "↘", "SINGLE_DOWN": "↓", "DOUBLE_DOWN": "⇊"
                }
                trend = trend_arrows.get(blood_sugar['trend'], blood_sugar['trend'])
                self.trend_label.config(text=f"{trend}")
                self.time_label.config(text=f"Updated: {blood_sugar['time'].strftime('%H:%M:%S')}")
            else:
                self.value_label.config(text="No data", fg='#ECF0F1')
                self.trend_label.config(text="")
                self.time_label.config(text="")
                self.stop_flashing()
        except Exception as e:
            print(f"Error updating: {e}")
            self.value_label.config(text="Error", fg='#E74C3C')
            self.trend_label.config(text="")
            self.time_label.config(text="")
            self.stop_flashing()
        finally:
            self.update_id = self.master.after(6000, self.update_value)

    def flash_widget(self):
        if self.is_flashing:
            current_bg = self.canvas.itemcget("background", "fill")
            new_bg = "#E74C3C" if current_bg == "#2C3E50" else "#2C3E50"
            self.canvas.itemconfig("background", fill=new_bg, outline=new_bg)
            self.flash_id = self.master.after(250, self.flash_widget)

    def stop_flashing(self):
        if self.flash_id:
            self.master.after_cancel(self.flash_id)
        self.is_flashing = False
        self.canvas.itemconfig("background", fill="#2C3E50", outline="#2C3E50")

    def clear_credentials(self):
        if os.path.exists('dexcom_config.json'):
            os.remove('dexcom_config.json')
        self.close_app()

    def close_app(self):
        if self.update_id:
            self.master.after_cancel(self.update_id)
        if self.flash_id:
            self.master.after_cancel(self.flash_id)
        self.icon.stop()  # Stop the system tray icon
        self.master.quit()
        self.master.destroy()
        print("Application closed")  # Add this line for debugging

    def create_image(self):
        # Create a simple image for the system tray icon
        image = Image.new('RGB', (64, 64), color = (46, 204, 113))
        return image

    def setup_system_tray(self):
        image = self.create_image()
        menu = pystray.Menu(
            pystray.MenuItem('Show', self.show_widget),
            pystray.MenuItem('Exit', self.exit_app)
        )
        self.icon = pystray.Icon("blood_sugar_widget", image, "Blood Sugar Widget", menu)
        self.icon.run_detached()
        print("System tray icon created")  # Add this line for debugging

    def show_widget(self):
        self.master.deiconify()
        self.master.lift()
        self.master.focus_force()
        self.master.attributes('-topmost', True)  # Ensure it appears on top
        self.master.after(1000, lambda: self.master.attributes('-topmost', False))  # Remove topmost after a second
        print("Widget restored")  # Add this line for debugging

    def exit_app(self):
        self.icon.stop()
        self.close_app()

    def minimize_widget(self):
        self.master.withdraw()
        self.icon.visible = True  # Ensure the icon is visible when minimized
        print("Widget minimized")  # Add this line for debugging

if __name__ == "__main__":
    root = ctk.CTk()
    widget = BloodSugarWidget(root)
    root.mainloop()
