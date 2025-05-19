# Garmin Overlay

> This project was vibe coded in a couple of hours.

A Python tool to overlay Garmin FIT data onto MP4 videos with real-time metrics and route visualization.

## Overview

**Garmin Overlay** is an open-source Python application that lets you add data overlays from your Garmin FIT files directly onto your running, cycling, or activity videos (MP4). Visualize heart rate, speed, cadence, elevation, distance, and your GPS route as a mini-map—perfect for sharing your workouts or races on YouTube, Strava, or social media.

## Features

- Overlay Garmin FIT data onto MP4 videos
- Import FIT files from Garmin devices or Garmin Connect
- Import video files of your run, ride, or activity
- Sync FIT data with video using time offset controls
- Display real-time metrics:
  - Heart Rate (bpm)
  - Speed (km/h)
  - Cadence (steps per minute)
  - Elevation (meters)
  - Distance (kilometers)
  - Mini-map with GPS route
  - Time
- Preview overlays before exporting
- Export to MP4 video with overlays for easy sharing
- Simple, intuitive GUI (Graphical User Interface)
- Fast setup with [uv](https://github.com/astral-sh/uv) and `pyproject.toml`

## Installation

1. **Install [uv](https://github.com/astral-sh/uv) (fast Python package installer):**

   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

2. **Create a virtual environment:**

   ```bash
   uv venv
   ```

3. **Activate the virtual environment:**

   - On Linux/macOS:
     ```bash
     source .venv/bin/activate
     ```
   - On Windows:
     ```cmd
     .venv\Scripts\activate
     ```

4. **Install dependencies using `uv` and `pyproject.toml`:**

   ```bash
   uv sync
   ```

## Usage

1. **Prepare your files:**
   - Place your `.mp4` video and `.fit` data files in the project directory.

2. **Run the overlay application:**

   ```bash
   uv run gpx_video_overlay.py
   ```

   This will open the GUI application, which is straightforward.

3. **Export your video:**
   - Use the GUI to preview overlays and export your final MP4 with data overlays.

## Example Use Cases

- Add Garmin data overlays to your running, cycling, or hiking videos
- Create YouTube videos with live stats from your Garmin device
- Share your activity videos with friends, coaches, or on Strava

## Tips for Best Results

- Use a FIT file exported directly from your Garmin device or Garmin Connect.
- The FIT file should contain heart rate, cadence, and other metrics.
- For best synchronization, start recording your FIT data slightly before starting your video.
- Use the offset slider to fine-tune the alignment between your video and FIT data.
- The "Combined" display format provides the most comprehensive view of your metrics.

## Troubleshooting

- If no heart rate or cadence data appears, you can simply remove these from with the checklist in the UI.
- If the mini-map doesn't appear, ensure your FIT file contains valid GPS coordinates.
- For large videos, the export process may take some time.
- If you encounter memory issues, try using a lower resolution video.

## Notes

- Do **not** upload `.mp4` or `.fit` files to the repository.
- See `.gitignore` for excluded files.

## Contributing & Support

Feel free to create issues or pull requests for improvements or bug fixes.

If you find this project useful, you can [buy me a running gel](https://paypal.me/snedelkoski) on PayPal!

---

**Keywords:** Garmin overlay, FIT overlay, MP4 overlay, Garmin video overlay, Garmin data video, running video overlay, cycling video overlay, Garmin metrics, GPX overlay, activity video stats, Garmin Connect, Strava video, heart rate overlay, speed overlay, cadence overlay, elevation overlay, GPS route overlay, open source, Python, uv, pyproject.toml
