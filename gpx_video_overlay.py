import tkinter as tk
from tkinter import filedialog, ttk
import cv2
import numpy as np
import gpxpy
import datetime
import os
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.backends.backend_agg import FigureCanvasAgg
from PIL import Image, ImageTk
import pandas as pd
from bisect import bisect_left
import threading
import pytz  # Add pytz for timezone support

class GPXVideoOverlay:
    def __init__(self, root):
        self.root = root
        self.root.title("Garmin .FIT Video Overlay")  # Rename the tool
        
        # Make window open in full screen
        screen_width = root.winfo_screenwidth()
        screen_height = root.winfo_screenheight()
        self.root.geometry(f"{screen_width}x{screen_height}")
        
        # Variables
        self.video_path = None
        self.gpx_path = None
        self.output_path = None
        self.gpx_data = None
        self.video_cap = None
        self.current_frame = None
        self.current_frame_idx = 0
        self.total_frames = 0
        self.video_fps = 0
        self.video_duration = 0
        self.overlay_settings = {
            'heart_rate': True,
            'speed': True,
            'cadence': True,
            'elevation': True,
            'distance': True,
            'map': True,
            'time': True,
            'activity_type': True,
            'avg_heart_rate': True,
            'avg_speed': True  # Retain only relevant fields
        }
        
        self.gpx_start_offset = 0  # Offset in seconds
        self.metrics_display_format = 'text'  # Only text option available
        self.rotate_180 = tk.BooleanVar(value=False)  # Add variable for rotation
        self.timezone = pytz.timezone("Europe/Berlin")  # Default timezone
        self.available_timezones = sorted(pytz.all_timezones)
        self._fields_dirty = False  # Track if any field was changed
        self.preview_playing = False  # Add this line to track preview state
        self.map_size = 300  # Size of the map overlay
        self.route_points = None  # Store route points for map
        self.map_img = None  # Store the map image
        self.min_lat = None  # Store map bounds
        self.max_lat = None
        self.min_lon = None
        self.max_lon = None

        # Replace with simple ASCII icons that work everywhere
        self.ICONS = {
            'heart_rate': 'HR  ',
            'speed': 'SPD ',
            'cadence': 'CAD ',
            'elevation': 'ALT ',
            'distance': 'DST ',
            'time': 'TME ',
            'avg_heart_rate': 'AHR ',
            'avg_speed': 'ASP ',
            'activity_type': 'ACT '  # Add icon for activity type
        }

        # Try to load a modern font, fallback to default if not available
        try:
            import cv2.freetype
            self.has_custom_font = True
        except:
            self.has_custom_font = False

        self.play_icon = "▶"    # Unicode play symbol
        self.pause_icon = "⏸"   # Unicode pause symbol
        self.stop_icon = "⏹"    # Unicode stop symbol

        self.create_widgets()
    
    def create_widgets(self):
        # Main frame structure with specific weights
        self.left_frame = ttk.Frame(self.root, padding=10)
        self.left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=False, padx=(0, 5))
        
        self.right_frame = ttk.Frame(self.root, padding=10)
        self.right_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)  # Changed from RIGHT to LEFT
        
        # File Selection Section
        file_frame = ttk.LabelFrame(self.left_frame, text="File Selection", padding=10)
        file_frame.pack(fill=tk.X, pady=5)
        
        ttk.Button(file_frame, text="Select Video", command=self.select_video).pack(fill=tk.X, pady=2)
        self.video_label = ttk.Label(file_frame, text="No video selected")
        self.video_label.pack(fill=tk.X, pady=2)
        
        ttk.Button(file_frame, text="Select FIT File", command=self.select_fit).pack(fill=tk.X, pady=2)  # Rename button
        self.gpx_label = ttk.Label(file_frame, text="No FIT file selected")  # Update label
        self.gpx_label.pack(fill=tk.X, pady=2)
        
        ttk.Button(file_frame, text="Set Output", command=self.select_output).pack(fill=tk.X, pady=2)
        self.output_label = ttk.Label(file_frame, text="No output selected")
        self.output_label.pack(fill=tk.X, pady=2)
        
        # Sync Section
        sync_frame = ttk.LabelFrame(self.left_frame, text="Sync Settings", padding=10)
        sync_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(sync_frame, text="GPX Start Offset (seconds):").pack(anchor=tk.W)
        self.offset_var = tk.DoubleVar(value=0.0)
        self.offset_scale = ttk.Scale(sync_frame, from_=-60.0, to=60.0, orient=tk.HORIZONTAL, 
                                      variable=self.offset_var, command=self._on_offset_change)
        self.offset_scale.pack(fill=tk.X, pady=2)
        self.offset_label = ttk.Label(sync_frame, text="0.0 s")
        self.offset_label.pack(anchor=tk.E)

        # Timezone selection
        ttk.Label(sync_frame, text="Timezone:").pack(anchor=tk.W, pady=(10, 0))
        self.timezone_var = tk.StringVar(value="Europe/Berlin")
        self.timezone_combo = ttk.Combobox(
            sync_frame, textvariable=self.timezone_var, values=self.available_timezones, width=30
        )
        self.timezone_combo.pack(fill=tk.X, pady=2)
        self.timezone_combo.bind("<<ComboboxSelected>>", self._on_field_change)
        
        # Overlay Settings Section
        overlay_frame = ttk.LabelFrame(self.left_frame, text="Overlay Settings", padding=10)
        overlay_frame.pack(fill=tk.X, pady=5)
        
        # Create a canvas and scrollbar for scrolling
        canvas = tk.Canvas(overlay_frame, height=300)
        scrollbar = ttk.Scrollbar(overlay_frame, orient="vertical", command=canvas.yview)
        
        # Create a frame inside the canvas to hold the checkbuttons
        settings_frame = ttk.Frame(canvas)
        settings_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        # Add the settings frame to the canvas
        canvas.create_window((0, 0), window=settings_frame, anchor="nw", width=canvas.winfo_reqwidth())
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Pack the canvas and scrollbar
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 2))
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Make the canvas expand with the window
        overlay_frame.bind('<Configure>', lambda e: canvas.configure(width=e.width-45))
        
        # Enable mousewheel scrolling
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)
        
        # Metrics to display checkbuttons
        metrics = ['Heart Rate', 'Speed', 'Cadence', 'Elevation', 'Distance', 'Map', 'Time',
                   'Activity Type', 'Avg Heart Rate', 'Avg Speed']  # Retain only relevant metrics
        self.metrics_vars = {}
        
        for metric in metrics:
            var = tk.BooleanVar(value=True)
            self.metrics_vars[metric.lower().replace(' ', '_')] = var
            ttk.Checkbutton(
                settings_frame, text=metric, variable=var,
                command=self._on_field_change
            ).pack(anchor=tk.W)
        
        # Add rotate 180° checkbox
        ttk.Checkbutton(
            settings_frame, text="Rotate 180°", variable=self.rotate_180,
            command=self._on_field_change
        ).pack(anchor=tk.W, pady=(5, 0))
        
        # Action buttons
        action_frame = ttk.Frame(self.left_frame)
        action_frame.pack(fill=tk.X, pady=10)
        
        ttk.Button(action_frame, text="Preview", command=self.preview_overlay).pack(side=tk.LEFT, padx=5)
        ttk.Button(action_frame, text="Export Video", command=self.export_video).pack(side=tk.RIGHT, padx=5)
        
        # Status bar (moved below action buttons)
        self.status_var = tk.StringVar(value="Ready")
        self.status_bar = ttk.Label(
            self.left_frame,  # Attach to left_frame, not action_frame
            textvariable=self.status_var,
            relief=tk.SUNKEN,
            anchor=tk.W,
            font=("TkDefaultFont", 12),  # Existing font
            padding=(10, 12),  # Existing padding
            width=30,  # Fixed width in characters
            wraplength=250  # Width in pixels before wrapping
        )
        self.status_bar.pack(fill=tk.X, pady=(5, 0))
        
        # Video preview area modifications
        preview_frame = ttk.LabelFrame(self.right_frame, text="Preview", padding=5)  # Reduced padding
        preview_frame.pack(fill=tk.BOTH, expand=True)
        
        self.canvas = tk.Canvas(preview_frame, bg="black")
        self.canvas.pack(fill=tk.BOTH, expand=True, padx=0, pady=0)  # Remove padding
        
        # Timeline slider with less vertical padding
        self.timeline_var = tk.DoubleVar(value=0)
        self.timeline = ttk.Scale(self.right_frame, from_=0, to=100, orient=tk.HORIZONTAL, 
                                 variable=self.timeline_var, command=self.update_timeline)
        self.timeline.pack(fill=tk.X, pady=(2, 0))  # Reduced top padding

        # Add playback controls frame
        controls_frame = ttk.Frame(self.right_frame)
        controls_frame.pack(fill=tk.X, pady=5)
        
        # Center the control buttons
        ttk.Label(controls_frame, text="").pack(side=tk.LEFT, expand=True)  # Spacer
        
        # Play/Pause button
        self.play_pause_btn = ttk.Button(
            controls_frame, 
            text=self.play_icon,
            width=3,
            style='PlayPause.TButton',
            command=self.toggle_play_pause
        )
        self.play_pause_btn.pack(side=tk.LEFT, padx=5)

        # Configure button style to show unicode characters properly
        style = ttk.Style()
        style.configure('PlayPause.TButton', font=('TkDefaultFont', 12))
        
        # Stop button
        ttk.Button(
            controls_frame,
            text=self.stop_icon,
            width=3,
            command=self.stop_preview
        ).pack(side=tk.LEFT, padx=5)

        # Create a label for current time / total time
        self.time_label = ttk.Label(controls_frame, text="00:00 / 00:00")
        self.time_label.pack(side=tk.LEFT, padx=5)
        
        ttk.Label(controls_frame, text="").pack(side=tk.LEFT, expand=True)  # Spacer
    
    def _on_field_change(self, *args):
        """Mark fields as dirty and update settings for preview."""
        self._fields_dirty = True
        # If preview is playing, stop it to prevent crashes
        if self.preview_playing:
            self.stop_preview()

    def stop_preview(self):
        """Stop video playback and reset to beginning"""
        self.pause_preview()  # First pause the playback
        
        # Reset to beginning
        if self.video_cap is not None:
            self.current_frame_idx = 0
            self.timeline_var.set(0)
            self.video_cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            ret, frame = self.video_cap.read()
            if ret:
                self.current_frame = frame
                self.display_frame()
                # Update time label
                self.time_label.config(text=f"00:00 / {int(self.video_duration//60):02d}:{int(self.video_duration%60):02d}")

    def toggle_play_pause(self):
        """Toggle between play and pause states"""
        if self.video_cap is None:
            self.status_var.set("Error: No video loaded")
            return
            
        if self.preview_playing:
            self.pause_preview()
            self.play_pause_btn.configure(text=self.play_icon)
        else:
            if self.current_frame_idx >= self.total_frames - 1:
                # If at the end, restart from beginning
                self.current_frame_idx = 0
                self.timeline_var.set(0)
                self.video_cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            self.play_preview()
            self.play_pause_btn.configure(text=self.pause_icon)
    
    def play_preview(self):
        """Start or resume video playback"""
        if self.video_cap is None:
            return
            
        self.preview_playing = True
        self.play_pause_btn.configure(text=self.pause_icon)
        self._preview_loop_after()
    
    def pause_preview(self):
        """Pause video playback"""
        self.preview_playing = False
        if hasattr(self, '_preview_after_id'):
            self.root.after_cancel(self._preview_after_id)
        self.play_pause_btn.configure(text=self.play_icon)

    def _on_offset_change(self, value=None):
        """Handle offset slider change."""
        self._fields_dirty = True
        self.offset_var.set(float(value))
        self.offset_label.config(text=f"{self.offset_var.get():.1f} s")

    def _apply_all_settings(self):
        """Apply all settings from UI fields to internal state."""
        # Overlay checkboxes
        for metric, var in self.metrics_vars.items():
            self.overlay_settings[metric] = var.get()
        # Display format
        self.metrics_display_format = 'text'
        # Rotation
        # (self.rotate_180 is already a BooleanVar, no need to copy)
        # Offset
        self.gpx_start_offset = self.offset_var.get()
        self.offset_label.config(text=f"{self.gpx_start_offset:.1f} s")
        # Timezone
        try:
            self.timezone = pytz.timezone(self.timezone_var.get())
        except Exception:
            self.timezone = pytz.timezone("Europe/Berlin")
            self.timezone_var.set("Europe/Berlin")
        self._fields_dirty = False

    def select_video(self):
        path = filedialog.askopenfilename(filetypes=[
            ("Video files", "*.mp4 *.avi *.mov *.mkv"),
            ("All files", "*.*")
        ])
        
        if path:
            self.video_path = path
            self.video_label.config(text=os.path.basename(path))
            self.load_video()
    
    def select_fit(self):
        path = filedialog.askopenfilename(filetypes=[
            ("FIT files", "*.fit"),  # Only allow .fit files
            ("All files", "*.*")
        ])
        
        if path:
            self.gpx_path = path
            self.gpx_label.config(text=os.path.basename(path))
            self.load_fit_file()  # Directly call load_fit_file
    
    def select_output(self):
        path = filedialog.asksaveasfilename(defaultextension=".mp4",
                                           filetypes=[("MP4 files", "*.mp4")])
        
        if path:
            self.output_path = path
            self.output_label.config(text=os.path.basename(path))
    
    def load_video(self):
        if self.video_path:
            cap = cv2.VideoCapture(self.video_path)
            if cap.isOpened():
                self.video_cap = cap
                self.total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                self.video_fps = cap.get(cv2.CAP_PROP_FPS)
                self.video_duration = self.total_frames / self.video_fps
                
                self.timeline.config(to=self.total_frames - 1)
                
                # Load first frame
                ret, frame = cap.read()
                if ret:
                    self.current_frame = frame
                    self.current_frame_idx = 0
                    self.display_frame()
                
                self.status_var.set(f"Video loaded: {self.total_frames} frames, {self.video_duration:.2f} seconds")
            else:
                self.status_var.set("Error: Could not open video file")
    
    def load_gpx(self):
        """Remove GPX support."""
        pass  # No longer needed

    def generate_route_map(self):
        """Generate a map with just the route line"""
        if not self.route_points:
            return

        # Create a new figure with black background
        fig, ax = plt.subplots(figsize=(8, 8), facecolor='black')
        ax.set_facecolor('black')
        ax.set_axis_off()

        # Get route bounds and store them for later use
        lats, lons = zip(*self.route_points)
        self.min_lat, self.max_lat = min(lats), max(lats)
        self.min_lon, self.max_lon = min(lons), max(lons)

        # Add some padding
        lat_pad = (self.max_lat - self.min_lat) * 0.1
        lon_pad = (self.max_lon - self.min_lon) * 0.1
        self.min_lat -= lat_pad
        self.max_lat += lat_pad
        self.min_lon -= lon_pad
        self.max_lon += lon_pad
        
        ax.set_ylim(self.min_lat, self.max_lat)
        ax.set_xlim(self.min_lon, self.max_lon)

        # Plot the route line with bright white color
        ax.plot(lons, lats, color='white', linewidth=5, alpha=1.0, solid_capstyle='round')

        # Convert to image
        canvas = FigureCanvasAgg(fig)
        canvas.draw()
        
        # Convert to numpy array with transparent background
        rgba = np.asarray(canvas.buffer_rgba())
        plt.close(fig)

        # Resize to desired size
        self.map_img = cv2.resize(rgba, (self.map_size, self.map_size), 
                                interpolation=cv2.INTER_AREA)

    def latlon_to_pixels(self, lat, lon):
        """Convert latitude/longitude to pixel coordinates on map"""
        # Normalize to 0-1
        if self.max_lon == self.min_lon or self.max_lat == self.min_lat:
            return 0, 0  # Avoid division by zero
        x_norm = (lon - self.min_lon) / (self.max_lon - self.min_lon)
        y_norm = (lat - self.min_lat) / (self.max_lat - self.min_lat)
        # Convert to pixel coordinates (invert y for image coordinates)
        x = int(x_norm * (self.map_size - 1))
        y = int((1 - y_norm) * (self.map_size - 1))
        # Clamp to image bounds
        x = max(0, min(self.map_size - 1, x))
        y = max(0, min(self.map_size - 1, y))
        return x, y

    def load_fit_file(self):
        """Load and parse .fit file data"""
        try:
            from fitparse import FitFile

            fitfile = FitFile(self.gpx_path)
            
            # Print available data fields from the first record message
            print("\nAvailable .FIT file parameters:")
            print("-" * 50)
            first_record = next(fitfile.get_messages('record'))
            fields_dict = {}
            
            for field in first_record:
                print(f"{field.name}: {field.value} {field.units}")
                field_value = field.value
                if field_value is not None:  # Only show fields that have values
                    fields_dict[field.name] = {
                        'value': field_value,
                        'units': field.units if field.units else 'none'
                    }
            
            # Print in a nicely formatted way
            print(f"{'Parameter':<30} {'Value':<20} {'Units'}")
            print("-" * 65)
            for name, info in sorted(fields_dict.items()):
                print(f"{name:<30} {str(info['value']):<20} {info['units']}")
            print("-" * 65 + "\n")

            data = []
            
            for record in fitfile.get_messages('record'):
                point_data = {
                    'time': None,
                    'latitude': None,
                    'longitude': None,
                    'elevation': None,
                    'heart_rate': None,
                    'cadence': None,
                    'speed': None,
                    'distance': None,
                    'activity_type': None,
                    'avg_heart_rate': None,
                    'avg_speed': None  # Retain only relevant fields
                }
                
                # Extract data from record
                for field in record:
                    if field.name == 'timestamp':
                        point_data['time'] = field.value
                    elif field.name == 'position_lat':
                        # Convert semicircles to degrees
                        if field.value is not None:
                            point_data['latitude'] = field.value * 180.0 / 2**31
                    elif field.name == 'position_long':
                        # Convert semicircles to degrees
                        if field.value is not None:
                            point_data['longitude'] = field.value * 180.0 / 2**31
                    elif field.name == 'enhanced_altitude':  # Prefer enhanced_altitude over altitude
                        point_data['elevation'] = field.value
                    elif field.name == 'enhanced_speed':  # Prefer enhanced_speed over speed
                        # Already in m/s, no need to convert
                        point_data['speed'] = field.value
                    elif field.name == 'heart_rate':
                        point_data['heart_rate'] = field.value
                    elif field.name == 'cadence':
                        point_data['cadence'] = field.value
                    elif field.name == 'distance':
                        point_data['distance'] = field.value
                    elif field.name == 'activity_type':
                        point_data['activity_type'] = field.value
                    elif field.name == 'avg_heart_rate':
                        point_data['avg_heart_rate'] = field.value
                    elif field.name == 'avg_speed':
                        point_data['avg_speed'] = field.value

                # Only add points that have position data
                if point_data['latitude'] is not None and point_data['longitude'] is not None:
                    data.append(point_data)
            
            # Convert to DataFrame for easier manipulation
            self.gpx_data = pd.DataFrame(data)
            
            # Display summary with additional metrics
            if not self.gpx_data.empty:
                start_time = self.gpx_data['time'].min()
                end_time = self.gpx_data['time'].max()
                duration = (end_time - start_time).total_seconds() / 60
                
                summary = (f"Start: {start_time.strftime('%H:%M:%S')}, "
                          f"End: {end_time.strftime('%H:%M:%S')}, "
                          f"Duration: {duration:.1f} min")
                
                # Add activity type if available
                if not self.gpx_data['activity_type'].isna().all():
                    activity = self.gpx_data['activity_type'].iloc[0]
                    summary += f", Activity: {activity}"
                
                # Add other metrics
                if not self.gpx_data['heart_rate'].isna().all():
                    avg_hr = self.gpx_data['heart_rate'].mean()
                    max_hr = self.gpx_data['heart_rate'].max()
                    summary += f", Avg HR: {avg_hr:.0f}, Max HR: {max_hr:.0f}"
                
                if not self.gpx_data['speed'].isna().all():
                    avg_speed = self.gpx_data['speed'] * 3.6  # Convert to km/h
                    max_speed = self.gpx_data['speed'].max() * 3.6
                    summary += f", Avg Speed: {avg_speed.mean():.1f} km/h, Max: {max_speed:.1f} km/h"
                
                self.status_var.set(summary)

                # After loading FIT data, prepare route points for map
                if not self.gpx_data.empty:
                    self.route_points = list(zip(
                        self.gpx_data['latitude'].tolist(),
                        self.gpx_data['longitude'].tolist()
                    ))
                    self.generate_route_map()
                
        except Exception as e:
            self.status_var.set(f"Error loading FIT file: {str(e)}")

    def calculate_speed(self, data):
        """Calculate speed between points in m/s"""
        speeds = [0]  # First point has no speed
        
        for i in range(1, len(data)):
            prev_point = data.iloc[i-1]
            curr_point = data.iloc[i]
            
            if prev_point['time'] and curr_point['time']:
                # Calculate time difference in seconds
                time_diff = (curr_point['time'] - prev_point['time']).total_seconds()
                
                if time_diff > 0:
                    # Calculate distance using haversine formula
                    from math import radians, sin, cos, sqrt, atan2
                    
                    lat1, lon1 = radians(prev_point['latitude']), radians(prev_point['longitude'])
                    lat2, lon2 = radians(curr_point['latitude']), radians(curr_point['longitude'])
                    
                    # Haversine formula
                    R = 6371000  # Earth radius in meters
                    dlon = lon2 - lon1
                    dlat = lat2 - lat1
                    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
                    c = 2 * atan2(sqrt(a), sqrt(1-a))
                    distance = R * c
                    
                    # Account for elevation change
                    if prev_point['elevation'] is not None and curr_point['elevation'] is not None:
                        ele_diff = curr_point['elevation'] - prev_point['elevation']
                        distance = sqrt(distance**2 + ele_diff**2)
                    
                    speed = distance / time_diff  # m/s
                    speeds.append(speed)
                else:
                    speeds.append(0)
            else:
                speeds.append(0)
        
        return speeds
    
    def calculate_distance(self, data):
        """Calculate cumulative distance in meters"""
        distances = [0]  # First point has no distance
        total_distance = 0
        
        for i in range(1, len(data)):
            prev_point = data.iloc[i-1]
            curr_point = data.iloc[i]
            
            # Calculate distance using haversine formula
            from math import radians, sin, cos, sqrt, atan2
            
            lat1, lon1 = radians(prev_point['latitude']), radians(prev_point['longitude'])
            lat2, lon2 = radians(curr_point['latitude']), radians(curr_point['longitude'])
            
            # Haversine formula
            R = 6371000  # Earth radius in meters
            dlon = lon2 - lon1
            dlat = lat2 - lat1
            a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
            c = 2 * atan2(sqrt(a), sqrt(1-a))
            distance = R * c
            
            # Account for elevation change
            if prev_point['elevation'] is not None and curr_point['elevation'] is not None:
                ele_diff = curr_point['elevation'] - prev_point['elevation']
                distance = sqrt(distance**2 + ele_diff**2)
            
            total_distance += distance
            distances.append(total_distance)
        
        return distances
    
    def update_offset(self, value=None):
        """Update GPX time offset (for legacy direct calls)."""
        self._apply_all_settings()
        if self.current_frame is not None and self.gpx_data is not None:
            self.display_frame()
    
    def update_overlay_settings(self):
        """Update which metrics to display and rotation (for legacy direct calls)."""
        self._apply_all_settings()
        if self.current_frame is not None:
            self.display_frame()
    
    def update_display_format(self):
        """Update how metrics are displayed (for legacy direct calls)."""
        self._apply_all_settings()
        if self.current_frame is not None:
            self.display_frame()
    
    def update_timeline(self, value=None):
        """Update frame based on timeline position"""
        # Stop preview when manually adjusting timeline
        if self.preview_playing:
            self.stop_preview()

        if self.video_cap is not None:
            frame_idx = int(self.timeline_var.get())
            
            if frame_idx != self.current_frame_idx:
                self.current_frame_idx = frame_idx
                self.video_cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
                ret, frame = self.video_cap.read()
                
                if ret:
                    self.current_frame = frame
                    self.display_frame()
                    # Update time label
                    current_time = frame_idx / self.video_fps
                    total_time = self.video_duration
                    self.time_label.config(
                        text=f"{int(current_time//60):02d}:{int(current_time%60):02d} / "
                             f"{int(total_time//60):02d}:{int(total_time%60):02d}"
                    )
    
    def update_timezone(self, event=None):
        """Update the timezone used for displaying time (for legacy direct calls)."""
        self._apply_all_settings()
        if self.current_frame is not None:
            self.display_frame()
    
    def get_gpx_data_at_time(self, video_time):
        """Get GPX data at the given video time, accounting for offset"""
        if self.gpx_data is None or self.gpx_data.empty:
            return None
        
        # Adjusted time with offset
        adjusted_time = video_time + self.gpx_start_offset
        
        if adjusted_time < 0:
            # Before GPX data starts
            return None
        
        # Get start time of GPX data
        gpx_start_time = self.gpx_data['time'].min()
        
        # Calculate target time
        target_time = gpx_start_time + datetime.timedelta(seconds=adjusted_time)
        
        # Find closest time in GPX data
        time_list = self.gpx_data['time'].tolist()
        idx = bisect_left(time_list, target_time)
        
        if idx >= len(time_list):
            idx = len(time_list) - 1
        elif idx > 0:
            # Check if previous point is closer
            if (target_time - time_list[idx-1]) < (time_list[idx] - target_time):
                idx = idx - 1

        # Compute cumulative averages for heart rate and speed
        if idx >= 0:
            valid_hr = self.gpx_data['heart_rate'][:idx + 1].dropna()
            valid_speed = self.gpx_data['speed'][:idx + 1].dropna()
            
            avg_heart_rate = valid_hr.mean() if not valid_hr.empty else None
            avg_speed = valid_speed.mean() if not valid_speed.empty else None
            
            self.gpx_data.at[idx, 'avg_heart_rate'] = avg_heart_rate
            self.gpx_data.at[idx, 'avg_speed'] = avg_speed

        return self.gpx_data.iloc[idx]
    
    def create_overlay_image(self, frame, gpx_point):
        """Create overlay image with metrics in F1-style"""
        if gpx_point is None:
            return frame

        h, w = frame.shape[:2]
        overlay = frame.copy()

        # Add other overlays (time, heart rate, etc.)
        # Create base position and styling
        margin = 20
        box_height = 38  # smaller height
        box_padding = 10  # smaller padding
        box_spacing = 2
        current_y = margin
        current_x = margin
        fixed_width = 180  # smaller width
        font_size = 0.55  # smaller font
        font_thickness = 1  # thinner font

        bg_color = (16, 16, 16)
        alpha = 0.65

        metrics = []
        
        if self.overlay_settings['activity_type'] and gpx_point.get('activity_type') is not None:
            metrics.append(('activity_type', f"{self.ICONS['activity_type']} {gpx_point['activity_type']}"))

        if self.overlay_settings['time']:
            gpx_time = gpx_point['time']
            if gpx_time.tzinfo is None:
                gpx_time = pytz.utc.localize(gpx_time)
            local_time = gpx_time.astimezone(self.timezone)
            metrics.append(('time', f"{self.ICONS['time']} {local_time.strftime('%H:%M:%S')}"))
        
        if self.overlay_settings['heart_rate'] and gpx_point.get('heart_rate') is not None:
            metrics.append(('heart_rate', f"{self.ICONS['heart_rate']} {int(gpx_point['heart_rate'])} BPM"))
        
        if self.overlay_settings['speed'] and gpx_point.get('speed') is not None:
            speed_kmh = gpx_point['speed'] * 3.6
            if speed_kmh > 0:
                pace_per_km = 60 / speed_kmh  # Calculate pace in minutes per km
                minutes = int(pace_per_km)
                seconds = int((pace_per_km - minutes) * 60)
                metrics.append(('speed', f"{self.ICONS['speed']} {minutes}:{seconds:02d} /km"))
            else:
                metrics.append(('speed', f"{self.ICONS['speed']} --:-- /km"))

        if self.overlay_settings['avg_heart_rate'] and gpx_point.get('avg_heart_rate') is not None:
            metrics.append(('avg_heart_rate', f"{self.ICONS['avg_heart_rate']} {int(gpx_point['avg_heart_rate'])} BPM"))

        if self.overlay_settings['avg_speed'] and gpx_point.get('avg_speed') is not None:
            avg_speed_kmh = gpx_point['avg_speed'] * 3.6  # Convert to km/h
            if avg_speed_kmh > 0:
                avg_pace_per_km = 60 / avg_speed_kmh  # Calculate average pace in minutes per km
                minutes = int(avg_pace_per_km)
                seconds = int((avg_pace_per_km - minutes) * 60)
                metrics.append(('avg_speed', f"{self.ICONS['avg_speed']} {minutes}:{seconds:02d} /km"))
            else:
                metrics.append(('avg_speed', f"{self.ICONS['avg_speed']} --:-- /km"))

        if self.overlay_settings['cadence'] and gpx_point.get('cadence') is not None:
            metrics.append(('cadence', f"{self.ICONS['cadence']} {int(gpx_point['cadence'])} SPM"))

        if self.overlay_settings['elevation'] and gpx_point.get('elevation') is not None:
            metrics.append(('elevation', f"{self.ICONS['elevation']} {int(gpx_point['elevation'])}m"))

        if self.overlay_settings['distance'] and gpx_point.get('distance') is not None:
            distance_km = gpx_point['distance'] / 1000
            metrics.append(('distance', f"{self.ICONS['distance']} {distance_km:.2f}km"))

        # Draw the overlays
        overlay_layer = overlay.copy()

        for i, (metric_type, text) in enumerate(metrics):
            # Draw background box with fixed width
            pts = np.array([
                [current_x, current_y],
                [current_x + fixed_width, current_y],
                [current_x + fixed_width, current_y + box_height],
                [current_x, current_y + box_height]
            ], np.int32)
            
            cv2.fillPoly(overlay_layer, [pts], bg_color)
            cv2.polylines(overlay_layer, [pts], True, (64, 64, 64), 1, cv2.LINE_AA)
            
            # Left-align text with padding
            text_x = int(current_x + box_padding)  # Convert to integer
            text_y = int(current_y + (box_height * 0.7))  # Convert to integer and adjust vertical position
            
            if self.has_custom_font:
                try:
                    font_face = cv2.freetype.createFreeType2()
                    font_face.loadFontData(self.font_path, 0)
                    font_face.putText(overlay_layer, text,
                                    (text_x, text_y),
                                    box_height-box_padding*2,
                                    (255, 255, 255), -1, cv2.LINE_AA)
                except Exception:
                    # Fallback to default font if custom font fails
                    cv2.putText(overlay_layer, text,
                              (text_x, text_y),
                              cv2.FONT_HERSHEY_SIMPLEX,
                              font_size, (255, 255, 255),
                              font_thickness, cv2.LINE_AA)
            else:
                cv2.putText(overlay_layer, text,
                          (text_x, text_y),
                          cv2.FONT_HERSHEY_SIMPLEX,
                          font_size, (255, 255, 255),
                          font_thickness, cv2.LINE_AA)
            
            current_y += box_height + box_spacing

        # Blend the overlay layer with the original frame
        overlay = cv2.addWeighted(overlay, 1-alpha, overlay_layer, alpha, 0)

        return overlay
    
    def display_frame(self):
        """Display current frame with overlays"""
        if self.current_frame is None:
            return

        # Get base frame and apply rotation if needed
        frame = cv2.rotate(self.current_frame, cv2.ROTATE_180) if self.rotate_180.get() else self.current_frame.copy()

        # Calculate video time
        video_time = self.current_frame_idx / self.video_fps

        # Get GPX data for this time
        gpx_point = self.get_gpx_data_at_time(video_time)

        # Create overlay
        frame_with_overlay = self.create_overlay_image(frame, gpx_point)

        # Convert to RGB for tkinter
        frame_rgb = cv2.cvtColor(frame_with_overlay, cv2.COLOR_BGR2RGB)
        frame_pil = Image.fromarray(frame_rgb)
        
        # Get current canvas size
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        
        if canvas_width > 1 and canvas_height > 1:  # Check if canvas is realized
            img_h, img_w = frame_rgb.shape[:2]
            aspect_ratio = img_w / img_h
            
            # Calculate new dimensions to fill canvas while preserving aspect ratio
            canvas_ratio = canvas_width / canvas_height
            
            if canvas_ratio > aspect_ratio:
                # Canvas is wider than video
                new_height = canvas_height
                new_width = int(new_height * aspect_ratio)
            else:
                # Canvas is taller than video
                new_width = canvas_width
                new_height = int(new_width / aspect_ratio)
            
            # Resize the image
            frame_pil = frame_pil.resize((new_width, new_height), Image.LANCZOS)
        
        # Convert to PhotoImage
        self.photo = ImageTk.PhotoImage(frame_pil)
        
        # Center the image in canvas
        x = (canvas_width - frame_pil.width) // 2
        y = (canvas_height - frame_pil.height) // 2
        
        # Clear previous image and draw new one
        self.canvas.delete("all")
        self.canvas.create_image(x, y, anchor=tk.NW, image=self.photo)
        
        # Update status with time info
        time_str = f"{int(video_time // 60):02d}:{int(video_time % 60):02d}"
        total_time_str = f"{int(self.video_duration // 60):02d}:{int(self.video_duration % 60):02d}"
        self.status_var.set(f"Frame: {self.current_frame_idx}/{self.total_frames}, Time: {time_str}/{total_time_str}")
    
    def preview_overlay(self):
        """Preview video with overlays"""
        if self.video_cap is None or self.gpx_data is None:
            self.status_var.set("Error: Load both video and FIT files first")
            return
            
        self.stop_preview()  # Reset everything
        self.play_preview()  # Start playback

    def _preview_loop_after(self):
        """Preview loop using Tkinter's after() for thread safety."""
        if not self.preview_playing or self.current_frame_idx >= self.total_frames:
            if self.current_frame_idx >= self.total_frames:
                self.stop_preview()  # Reset to beginning when reaching the end
            return

        try:
            self.video_cap.set(cv2.CAP_PROP_POS_FRAMES, self.current_frame_idx)
            ret, frame = self.video_cap.read()
            if not ret:
                self.stop_preview()
                return

            self.current_frame = frame
            self.timeline_var.set(self.current_frame_idx)
            self.display_frame()
            
            # Update time label
            current_time = self.current_frame_idx / self.video_fps
            total_time = self.video_duration
            self.time_label.config(
                text=f"{int(current_time//60):02d}:{int(current_time%60):02d} / "
                     f"{int(total_time//60):02d}:{int(total_time%60):02d}"
            )
            
            self.current_frame_idx += 1
            wait_ms = int(1000 / self.video_fps)
            self._preview_after_id = self.root.after(wait_ms, self._preview_loop_after)
        except Exception as e:
            self.stop_preview()
            self.status_var.set(f"Preview error: {str(e)}")
    
    def export_video(self):
        """Export video with overlays"""
        if self.video_cap is None or self.gpx_data is None or self.output_path is None:
            self.status_var.set("Error: Please select video, FIT file, and output path")
            return

        self.video_cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
        width = int(self.video_cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(self.video_cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = self.video_cap.get(cv2.CAP_PROP_FPS)

        # Always use input resolution and fps for output
        if hasattr(self, 'min_duration') and self.min_duration is not None:
            max_frames = int(self.min_duration * fps)
        else:
            max_frames = int(self.video_cap.get(cv2.CAP_PROP_FRAME_COUNT))

        temp_output = os.path.splitext(self.output_path)[0] + "_temp.avi"
        # Use FFV1 lossless codec for temp AVI to avoid quality loss
        fourcc = cv2.VideoWriter_fourcc(*'FFV1')
        out = cv2.VideoWriter(temp_output, fourcc, fps, (width, height))

        if not out.isOpened():
            self.status_var.set("Error: Could not create output video writer")
            return

        frame_idx = 0
        self.status_var.set(f"Starting export: Processing {max_frames} frames...")
        self.root.update()

        try:
            while frame_idx < max_frames:
                self.video_cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
                ret, frame = self.video_cap.read()
                if not ret:
                    break
                if self.rotate_180.get():
                    frame = cv2.rotate(frame, cv2.ROTATE_180)
                video_time = frame_idx / fps
                gpx_point = self.get_gpx_data_at_time(video_time)
                frame_with_overlay = self.create_overlay_image(frame, gpx_point)
                # Write frame with same resolution as input
                out.write(frame_with_overlay)
                frame_idx += 1
                progress = int(frame_idx / max_frames * 100)
                self.status_var.set(f"Exporting: {progress}% ({frame_idx}/{max_frames})")
                if frame_idx % 30 == 0:
                    self.root.update()
            out.release()

            # Ensure the file is flushed and closed before conversion
            import time
            time.sleep(0.5)

            # Use ffmpeg to combine the overlayed video with the original audio
            try:
                import subprocess
                # Check if ffmpeg is available
                try:
                    subprocess.check_output(['ffmpeg', '-version'], stderr=subprocess.STDOUT)
                    has_ffmpeg = True
                except Exception:
                    has_ffmpeg = False

                if has_ffmpeg:
                    final_output = self.output_path
                    # Use -crf 18 for visually lossless H.264 output
                    cmd = [
                        'ffmpeg', '-y',
                        '-i', temp_output,      # Input: video with overlays (lossless)
                        '-i', self.video_path,  # Input: original video for audio
                        '-c:v', 'libx264',      # Encode video to H.264
                        '-crf', '18',           # High quality (visually lossless)
                        '-preset', 'slow',      # Good quality preset
                        '-c:a', 'copy',         # Copy audio without re-encoding
                        '-map', '0:v:0',        # Take video from the first input
                        '-map', '1:a?',         # Automatically include all audio streams from the second input
                        '-movflags', '+faststart',
                        final_output
                    ]
                    subprocess.run(cmd, check=True)
                    if os.path.exists(temp_output):
                        os.remove(temp_output)
                    self.status_var.set(f"Export complete: {final_output}")
                else:
                    self.status_var.set("Error: ffmpeg is not available. Cannot add audio.")
            except Exception as e:
                self.status_var.set(f"Error during export: {str(e)}")
                if os.path.exists(temp_output):
                    os.remove(temp_output)

        except Exception as e:
            self.status_var.set(f"Error during export: {str(e)}")
            if out.isOpened():
                out.release()

        self.video_cap.set(cv2.CAP_PROP_POS_FRAMES, 0)


if __name__ == "__main__":
    root = tk.Tk()
    app = GPXVideoOverlay(root)
    root.mainloop()