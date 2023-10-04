import curses
from curses import wrapper
from curses.textpad import Textbox, rectangle
import datetime
import json
import logging
import math
import re
from subprocess import Popen, PIPE
from pathlib import Path
import textwrap

import pyperclip
import typer

app = typer.Typer()

start_time = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

#transcription = Path("/home/johannes/Videos/2023-10-03 16-01-13_arun_accidental_alien_actress_transcriptions/2023-10-03 16-01-13_arun_accidental_alien_actress.vtt")
#video = Path("/home/johannes/Videos/2023-10-03 16-01-13_arun_accidental_alien_actress.mkv")
mpv_socket = Path(f"/tmp/mpvsocket")

logging.basicConfig(level=logging.DEBUG)

logging.debug(f"Using mpv socket: {mpv_socket}")

def set_playback_position(pos):
    Popen(f'echo \'{{ "command": ["set_property", "playback-time", "{pos}"], "async": true }}\' | socat - {mpv_socket}', shell=True, stdout=PIPE, stderr=PIPE)

def get_pause():
        try:
            proc = Popen(f'echo \'{{ "command": ["get_property", "pause"], "async": true }}\' | socat - {mpv_socket}', shell=True, stdout=PIPE, stderr=PIPE)
            proc.wait()
            data = proc.communicate()
            data = data[0].decode("utf-8")
            data = json.loads(data)["data"]
            data = bool(data)
            return data
        except Exception as e:
            logging.error(e)
            return False

def set_pause(pause: bool):
    if pause is None or pause == "toggle":
        pause = not get_pause()

    if pause:
        play_v = "true"
    else:
        play_v = "false"
    Popen(f'echo \'{{ "command": ["set_property", "pause", {play_v}], "async": true }}\' | socat - {mpv_socket}', shell=True, stdout=PIPE, stderr=PIPE)

def display_transcription(stdscr, lines, offset):
    stdscr.clear()
    escape = False
    for line in lines[offset:]:
        for c in line:
            y, x = stdscr.getyx()
            if y >= curses.LINES-1 and (c == '\n' or x >= curses.COLS-1):
                escape = True
                break
            stdscr.addstr(c)
        if escape:
            break

def clamp_offset(offset, lines):
    return min(len(lines), max(0, offset))

def wrap_lines(lines):
    new_lines = []
    for line in lines:
        for i in textwrap.wrap(line, width=curses.COLS-1):
            new_lines.append(i + "\n")
    return new_lines

def main(stdscr, transcription: Path):
    curses.mousemask(-1)
    curses.mouseinterval(0)

    offset = 0

    with transcription.open() as f:
        lines = f.readlines()

    lines = list(wrap_lines(lines))

    display_transcription(stdscr, lines, offset)

    #Popen(["mpv", f"--input-ipc-server='{mpv_socket}'", "--speed=1.8", f"--sub-files='{transcription}'", f"{video}"], stdout=PIPE, stderr=PIPE)

    mouse_down_coords = (0, 0)
    while True:
        event = stdscr.getch()
        curses.update_lines_cols()
        if event == ord("q"): 
            break 
        if event == ord("j"):
            offset = clamp_offset(offset+1, lines)
            display_transcription(stdscr, lines, offset)
        if event == ord("k"):
            offset = clamp_offset(offset-1, lines)
            display_transcription(stdscr, lines, offset)
        if event == ord("d"):
            offset = clamp_offset(offset + int((curses.LINES-1)*0.5), lines)
            display_transcription(stdscr, lines, offset)
        if event == ord("u"):
            offset = clamp_offset(offset - int((curses.LINES-1)*0.5), lines)
            display_transcription(stdscr, lines, offset)
        if event == ord("p"):
            set_pause("toggle")
        if event == curses.KEY_MOUSE:
            _, mx, my, _, bstate = curses.getmouse()
            if (bstate & curses.BUTTON3_PRESSED != 0 or
                bstate & curses.BUTTON3_CLICKED != 0):
                clicked_line = lines[offset+my]
                while not re.match(r"(\d{2}:)?\d\d:\d\d\.\d\d\d", clicked_line):
                    my -= 1
                    clicked_line = lines[offset+my]
                # parse based on if hours are present in the timestamp
                if clicked_line[10:13] == "-->":
                    line_start = clicked_line[:9]
                else:
                    line_start = lines[offset+my][:12]

                set_playback_position(line_start)
                set_pause(False)
            if bstate & curses.BUTTON1_PRESSED != 0:
                mouse_down_coords = (mx, my)
            # Copy selection to clipboard
            if bstate & curses.BUTTON1_RELEASED != 0:
                result = ""
                for s in lines[offset+mouse_down_coords[1]:offset+my+1]:
                    s = s.strip()
                    if s == "" or re.match(r"(\d{2}:)?\d\d:\d\d\.\d\d\d", s):
                        continue
                    result += s + " "

                pyperclip.copy(result)

    curses.endwin()


def wrapper(file: Path):
    curses.wrapper(lambda stdscr: main(stdscr, file))

if __name__ == "__main__":
    typer.run(wrapper)
