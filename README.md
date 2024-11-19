# VESC B2B dyno

This repository allows users to run back-to-back dynamometer experiments using 2 VESCs.

## Instructions (for Windows only)

Pre-execution checklist:
* Make sure to run VESC motor parameter identification prior to run this B2B dyno script.
* Confirm that the motor has proper temperature sensing and that VESC protections are set properly. This script may damage the motor windings if there are no temperature protections in place.
* This script will work better at low speeds if the motors have hall effect sensors.

How to install and run a dyno routine:
1. Open a terminal in the repo directory `VESC_B2B_Dyno`.
2. Create a new virtual Python environment: `pip install virtualenv` and `python -m venv .venv`
3. Activate the virtual environment: `.venv/Scripts/activate`
4. Install all requirements: `pip install -r requirements.txt`
5. Run the python script: `python TorqueSpeedProfile.py`
6. When done running: `.venv/Scripts/deactivate`
7. Check the generated log file for VESC measurements at each operating point.
