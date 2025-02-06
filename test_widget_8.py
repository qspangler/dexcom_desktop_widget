import tkinter as tk
import customtkinter as ctk
from datetime import datetime
from pydexcom import Dexcom
from tkinter import font as tkfont
import tkinter.messagebox as tkmb
import json
import os
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.dates import DateFormatter, HourLocator
import matplotlib.dates as mdates

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class BloodSugarWidget:
    def __init__(self, master):
        self.master = master
        self.master.withdraw()
        self.login()
        self.history_data = []
        self.show_graph = False
        self.graph_canvas = None
        self.is_flashing = False
        self.flash_id = None

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
        self.master.quit()

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
        self.master.deiconify()
        self.setup_main_window()
        self.update_value()

    def setup_main_window(self):
        self.master.overrideredirect(True)
        self.master.attributes('-topmost', True)
        
        widget_width = 240
        widget_height = 160
        x = self.master.winfo_screenwidth() - widget_width - 10
        y = self.master.winfo_screenheight() - widget_height - 40
        self.master.geometry(f'{widget_width}x{widget_height}+{x}+{y}')

        # Control bar
        self.control_bar = tk.Frame(self.master, bg='#2C3E50', height=30)
        self.control_bar.pack(fill='x', side='top')
        
        # Toggle button
        self.toggle_button = tk.Button(self.control_bar, text="📈", command=self.toggle_view,
                                     bg='#2C3E50', fg='#ECF0F1', font=("Arial", 12),
                                     bd=0, highlightthickness=0)
        self.toggle_button.pack(side='left', padx=5)
        
        # Close button
        close_button = tk.Button(self.control_bar, text="×", command=self.close_app,
                               bg='#2C3E50', fg='#ECF0F1', font=("Arial", 16, "bold"),
                               bd=0, highlightthickness=0, padx=5, pady=0)
        close_button.pack(side='right')
        
        # Clear credentials button
        clear_button = tk.Button(self.control_bar, text="Clear Login", command=self.clear_credentials,
                               bg='#2C3E50', fg='#ECF0F1', font=("Arial", 8),
                               bd=0, highlightthickness=0)
        clear_button.pack(side='left', padx=5)

        # Minimize button
        minimize_button = tk.Button(self.control_bar, text="-", command=self.minimize_widget,
                                bg='#2C3E50', fg='#ECF0F1', font=("Arial", 16, "bold"),
                                bd=0, highlightthickness=0, padx=5, pady=0)
        minimize_button.pack(side='right')

        # Main display canvas
        self.main_canvas = tk.Canvas(self.master, bg='#2C3E50', bd=0, highlightthickness=0)
        self.main_canvas.pack(fill='both', expand=True)
        
        # Graph display frame
        self.graph_frame = tk.Frame(self.master, bg='#2C3E50')

        # Value display elements
        value_font = tkfont.Font(family="Helvetica", size=28, weight="bold")
        trend_font = tkfont.Font(family="Helvetica", size=18)
        time_font = tkfont.Font(family="Helvetica", size=10)
        
        self.value_label = tk.Label(self.main_canvas, text="Loading...", font=value_font,
                                  bg='#2C3E50', fg='#ECF0F1')
        self.value_label.place(relx=0.5, rely=0.35, anchor="center")
        
        self.trend_label = tk.Label(self.main_canvas, text="", font=trend_font,
                                  bg='#2C3E50', fg='#BDC3C7')
        self.trend_label.place(relx=0.5, rely=0.6, anchor="center")
        
        self.time_label = tk.Label(self.main_canvas, text="", font=time_font,
                                 bg='#2C3E50', fg='#95A5A6')
        self.time_label.place(relx=0.5, rely=0.85, anchor="center")
        
        # Dragging functionality
        self.control_bar.bind("<ButtonPress-1>", self.start_move)
        self.control_bar.bind("<B1-Motion>", self.do_move)
        self.main_canvas.bind("<Configure>", self.create_rounded_frame)

    def toggle_view(self):
        self.show_graph = not self.show_graph
        if self.show_graph:
            self.main_canvas.pack_forget()
            self.graph_frame.pack(fill='both', expand=True)
            self.draw_history_graph()
            self.toggle_button.config(text="¹²³")
        else:
            self.graph_frame.pack_forget()
            self.main_canvas.pack(fill='both', expand=True)
            self.toggle_button.config(text="📈")

    def draw_history_graph(self):
        if self.graph_canvas:
            self.graph_canvas.get_tk_widget().destroy()

        # Create figure with adjusted layout
        fig = plt.figure(figsize=(2.5, 1.8), dpi=100, facecolor='#2C3E50')
        ax = fig.add_subplot(111)
        
        # Adjust spacing around the plot
        fig.subplots_adjust(left=0.15, bottom=0.25, right=0.95, top=0.9)
        
        # Style adjustments
        ax.set_facecolor('#2C3E50')
        for spine in ax.spines.values():
            spine.set_color('#ECF0F1')
        ax.tick_params(axis='both', colors='#ECF0F1', labelsize=8)
        
        # Axis labels with padding
        ax.set_ylabel('mg/dL', color='#ECF0F1', labelpad=15)
        ax.set_xlabel('Time', color='#ECF0F1', labelpad=10)
        
        if self.history_data:
            times = [reading.datetime for reading in self.history_data]
            values = [reading.mg_dl for reading in self.history_data]
            
            # Create segments with different colors based on values
            for i in range(len(times)-1):
                # Get the coordinates for each segment
                x_seg = [times[i], times[i+1]]
                y_seg = [values[i], values[i+1]]
                
                # Determine color based on value
                if values[i] < 80:
                    color = '#FF0000'  # Red for low
                elif values[i] > 140:
                    color = '#FFA500'  # Orange for high
                else:
                    color = '#3498DB'  # Original blue for normal range
                    
                ax.plot(x_seg, y_seg, color=color, linewidth=2)
            
            # Date formatting
            ax.xaxis.set_major_locator(HourLocator(interval=3))
            ax.xaxis.set_major_formatter(DateFormatter('%H:%M'))
            
            # Rotate and align date labels
            fig.autofmt_xdate(rotation=0, ha='right')
            
            # Current value marker
            current_time = times[0]
            current_value = values[0]
            #ax.plot(current_time, current_value, '>', color='#2ECC71', markersize=4)

            # After setting the y-axis limits, add these lines:
            ax.axhline(y=80, color='#FF0000', linestyle='--', alpha=0.5)  # Red line at 80
            ax.axhline(y=140, color='#FFA500', linestyle='--', alpha=0.5)  # Orange line at 140
            
            # Set y-axis limits with padding
            y_min, y_max = min(values), max(values)
            ax.set_ylim(0, 400)

        self.graph_canvas = FigureCanvasTkAgg(fig, master=self.graph_frame)
        self.graph_canvas.draw()
        self.graph_canvas.get_tk_widget().pack(fill='both', expand=True)


        # self.graph_canvas = FigureCanvasTkAgg(fig, master=self.graph_frame)
        # self.graph_canvas.draw()
        # self.graph_canvas.get_tk_widget().pack(fill='both', expand=True)

    def create_rounded_frame(self, event):
        radius = 15
        self.main_canvas.delete("all")
        width, height = event.width, event.height
        
        self.main_canvas.create_rectangle(0, 0, width, height, fill='#2C3E50', outline='#2C3E50', tags="background")
        self.main_canvas.create_arc(0, 0, radius*2, radius*2, start=90, extent=90, fill='#2C3E50', outline='#2C3E50')
        self.main_canvas.create_arc(width-radius*2, 0, width, radius*2, start=0, extent=90, fill='#2C3E50', outline='#2C3E50')
        self.main_canvas.create_arc(0, height-radius*2, radius*2, height, start=180, extent=90, fill='#2C3E50', outline='#2C3E50')
        self.main_canvas.create_arc(width-radius*2, height-radius*2, width, height, start=270, extent=90, fill='#2C3E50', outline='#2C3E50')

    def start_move(self, event):
        self.x = event.x
        self.y = event.y

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
            return None
        except Exception as e:
            print(f"Error getting blood sugar: {e}")
            return None

    def update_value(self):
        try:
            dexcom = Dexcom(username=self.username, password=self.password)
            self.history_data = dexcom.get_glucose_readings(minutes=360)
            
            if self.show_graph:
                self.draw_history_graph()

            blood_sugar = self.get_blood_sugar()
            if blood_sugar:
                value = blood_sugar['value']
                self.value_label.config(text=f"{value} mg/dL")

                if value < 80:
                    color = '#E74C3C'
                    if not self.is_flashing:
                        self.is_flashing = True
                        self.flash_widget()
                elif value > 140:
                    color = '#F39C12'
                    self.stop_flashing()
                else:
                    color = '#2ECC71'
                    self.stop_flashing()
                
                self.value_label.config(fg=color)
                trend_arrows = {
                    "NONE": "→", "FLAT": "→", "FORTY_FIVE_UP": "↗",
                    "SINGLE_UP": "↑", "DOUBLE_UP": "⇈", "FORTY_FIVE_DOWN": "↘",
                    "SINGLE_DOWN": "↓", "DOUBLE_DOWN": "⇊"
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
            self.update_id = self.master.after(60000, self.update_value)

    def flash_widget(self):
        if self.is_flashing:
            current_bg = self.main_canvas.itemcget("background", "fill")
            new_bg = "#E74C3C" if current_bg == "#2C3E50" else "#2C3E50"
            self.main_canvas.itemconfig("background", fill=new_bg, outline=new_bg)
            self.flash_id = self.master.after(250, self.flash_widget)

    def stop_flashing(self):
        if self.flash_id:
            self.master.after_cancel(self.flash_id)
            self.is_flashing = False
            self.main_canvas.itemconfig("background", fill="#2C3E50", outline="#2C3E50")

    def clear_credentials(self):
        if os.path.exists('dexcom_config.json'):
            os.remove('dexcom_config.json')
        self.close_app()

    def close_app(self):
        if self.update_id:
            self.master.after_cancel(self.update_id)
        if self.flash_id:
            self.master.after_cancel(self.flash_id)
        self.master.quit()
        self.master.destroy()

    def minimize_widget(self):
        self.master.withdraw()  # Hide the window
        self.create_tray_icon()

    def create_tray_icon(self):
        import pystray
        from PIL import Image
        
        # Create a simple icon (you can replace with your own icon)
        icon_image = Image.new('RGB', (64, 64), color='#56A846')
        
        def restore_window(icon):
            icon.stop()
            self.master.after(0, self.restore_widget)
        
        # Create the tray icon
        self.tray_icon = pystray.Icon(
            "glucose_widget",
            icon_image,
            "Glucose Widget",
            menu=pystray.Menu(
                pystray.MenuItem("Display Widget", restore_window),
                pystray.MenuItem("Close", self.close_app)
            )
        )
        self.tray_icon.run()

    def restore_widget(self):
        self.master.deiconify()  # Show the window
        self.master.attributes('-topmost', True)  # Ensure it's on top


if __name__ == "__main__":
    root = ctk.CTk()
    widget = BloodSugarWidget(root)
    root.mainloop()
