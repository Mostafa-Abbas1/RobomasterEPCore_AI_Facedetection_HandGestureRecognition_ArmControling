"""
Main entry point for the Robomaster EP Core AI Controller.

Starts the integrated system with person tracking and gesture control.
The system begins in TRACKING mode (follows the closest person) and can
be toggled to GESTURE mode by showing both fists to the camera.

Usage:
    python main.py
"""

from src.control.decision_logic import run

if __name__ == "__main__":
    run()
