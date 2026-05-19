"""Convenience entry point for the GroundDesk Gradio demo."""

from app.interfaces.ui import build_interface


if __name__ == "__main__":
    build_interface().launch(server_name="0.0.0.0", server_port=7860)

