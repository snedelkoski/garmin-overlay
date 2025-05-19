# Garmin Overlay

A Python tool to overlay FIT data onto MP4 videos.

## Features

- Import FIT data from Garmin devices
- Import video files of your run
- Sync FIT data with video using time offset controls
- Display various metrics:
  - Heart Rate (bpm)
  - Speed (km/h)
  - Cadence (steps per minute)
  - Elevation (meters)
  - Distance (kilometers)
  - Mini-map showing your route
  - Time
- Choose between text-only, gauge-only, or combined display formats
- Preview the overlays before exporting
- Export to MP4 video with all overlays included

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

2. **Run the overlay script:**

   ```bash
   python gpx_video_overlay.py --video input.mp4 --data input.fit
   ```

   Replace `input.mp4` and `input.fit` with your actual filenames.

3. **Options:**
   - Run `python gpx_video_overlay.py --help` to see all available options.

## Tips for Best Results

- Use a FIT file exported directly from your Garmin device or Garmin Connect.
- The FIT file should contain heart rate, cadence, and other metrics.
- For best synchronization, start recording your FIT data slightly before starting your video.
- Use the offset slider to fine-tune the alignment between your video and FIT data.
- The "Combined" display format provides the most comprehensive view of your metrics.

## Troubleshooting

- If no heart rate or cadence data appears, make sure your FIT file includes these metrics.
- If the mini-map doesn't appear, ensure your FIT file contains valid GPS coordinates.
- For large videos, the export process may take some time.
- If you encounter memory issues, try using a lower resolution video.

## Notes

- Do **not** upload `.mp4` or `.fit` files to the repository.
- See `.gitignore` for excluded files.
