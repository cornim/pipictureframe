#!/usr/bin/python3

""" Simplified slideshow system using ImageSprite.
    Also has a minimal use of PointText and TextBlock system with reduced codepoints
and reduced grid_size to give better resolution for large characters.

USING exif info to rotate images
"""

import logging
import multiprocessing as mp
import os
import time
from logging.handlers import RotatingFileHandler

from pipictureframe.pi3dfuncs import Pi3dFuncs
from pipictureframe.picdb.Database import Database
from pipictureframe.picdb.PictureUpdater import update_pictures_in_db, PictureData
from pipictureframe.utils.Config import setup_parser, Config
from pipictureframe.utils.NextPictureManager import NextPictureManager

log = logging.getLogger()
log.setLevel(logging.DEBUG)


def start_pic_loading_process(conf: Config):
    pic_load_proc = mp.Process(
        target=update_pictures_in_db, args=(conf.pic_dir, conf.db_connection_str)
    )
    pic_load_proc.daemon = True
    pic_load_proc.start()
    return pic_load_proc


def load_next_slide(pi3dfuncs: Pi3dFuncs, cur_pic: PictureData, config):
    pi3dfuncs.copy_fg_to_bg()
    pi3dfuncs.load_fg(cur_pic, config)
    pi3dfuncs.set_textures()


def check_for_changes(last_file_change, pic_dir):
    update = False
    for root, _, _ in os.walk(pic_dir):
        mod_tm = os.stat(root).st_mtime
        if mod_tm > last_file_change:
            last_file_change = mod_tm
            update = True
    log.debug(f"Checked for updates to picture folder. Result = {update}")
    return update


class LoopControlVars:
    def __init__(self, config):
        self.cur_time = time.time()
        self.next_pic_time = self.cur_time + config.time_delay
        self.text_start_time = self.cur_time
        self.folder_recheck_time = self.cur_time + config.check_dir_tm
        # Initially pretend a transition has begun
        self.fg_alpha = 0
        self.text_alpha = 0
        self.transition_running = True

    def __repr__(self):
        return str(self.__dict__)


class DebugFileFilter(logging.Filter):
    def filter(self, record: logging.LogRecord):
        if record.levelno <= logging.DEBUG:
            if "PIL" in record.name or "pi3d" in record.name:
                return False
        return True


def configure_logging(config):
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    ch = logging.StreamHandler()
    ch.setLevel(config.log_level)
    ch.setFormatter(formatter)
    log.addHandler(ch)
    if config.debug_log_file:
        try:
            dfh = RotatingFileHandler(
                config.debug_log_file,
                maxBytes=10 * 1024 * 1024,
                backupCount=5,
                encoding="utf-8",
            )
            dfh.setLevel(logging.DEBUG)
            dfh.setFormatter(formatter)
            dfh.addFilter(DebugFileFilter())
            log.addHandler(dfh)
        except Exception as e:
            log.error(
                f"Could not open debug log file {config.debug_log_file}.", exc_info=e
            )
    log.debug(f"Starting application with following config:\n{config}")


def main():
    parser = setup_parser()
    args = parser.parse_args()
    config = Config(args)

    configure_logging(config)

    db = Database(config.db_connection_str)

    pic_loading_proc = start_pic_loading_process(config)

    pi3dfuncs = Pi3dFuncs(config)

    # Set values for first slide a part of ctor
    lcv = LoopControlVars(config)
    log.debug(f"Initialized loop control variables:\n{lcv}")

    npm = NextPictureManager(config, pic_loading_proc, db)
    cur_pic = npm.get_next_picture()

    # Load first picture into fg
    pi3dfuncs.load_fg(cur_pic, config)
    # Immediately copy it to bg
    pi3dfuncs.copy_fg_to_bg()
    pi3dfuncs.set_fg_bg_ratio(lcv.fg_alpha)
    pi3dfuncs.set_textures()
    pi3dfuncs.prepare_text(cur_pic, config)

    # TODO implement pause functionality
    while pi3dfuncs.display_loop_running():
        lcv.cur_time = time.time()
        if lcv.cur_time > lcv.next_pic_time and not lcv.transition_running:
            log.debug(f"Starting transition.\n{lcv}")
            lcv.text_start_time = lcv.cur_time
            lcv.next_pic_time = lcv.cur_time + config.time_delay
            pi3dfuncs.prepare_text(cur_pic, config)
            lcv.transition_running = True

        if lcv.transition_running:
            lcv.fg_alpha += config.delta_alpha
            lcv.text_alpha = lcv.fg_alpha
            if lcv.fg_alpha > 1.0:
                log.debug(f"Transition finished.\n{lcv}")
                # When the transition ends copy the slide shown to bg and load the next slide into fg
                lcv.transition_running = False
                cur_pic = npm.get_next_picture()
                load_next_slide(pi3dfuncs, cur_pic, config)
                lcv.fg_alpha = 0
            pi3dfuncs.set_fg_bg_ratio(lcv.fg_alpha)

        pi3dfuncs.draw_slide()

        # Text shouldn't be shown anymore, min is needed if show text time is longer than time delay
        if lcv.cur_time > lcv.text_start_time + min(
            config.show_text_tm, config.time_delay - 1
        ):
            if lcv.text_alpha > 0:
                lcv.text_alpha -= config.delta_alpha
            else:
                lcv.text_alpha = 0
            pi3dfuncs.set_text_alpha_and_draw(lcv.text_alpha)
        elif lcv.transition_running:
            pi3dfuncs.set_text_alpha_and_draw(lcv.text_alpha)
        else:
            pi3dfuncs.set_text_alpha_and_draw(1)

        # Also check that no transition is running to avoid artefacts:
        if (
            lcv.cur_time > lcv.folder_recheck_time
            and lcv.fg_alpha == 0
            and lcv.text_alpha == 0
        ):
            lcv.folder_recheck_time = lcv.cur_time + config.check_dir_tm
            if not pic_loading_proc.is_alive():
                pic_loading_proc = start_pic_loading_process(config)
                npm.reload_pictures()

        # TODO Fix keyboard input
        if config.keyboard:
            k = pi3dfuncs.keyboard.read()
            if k == 27:  # ESC
                break
            elif k == ord(" "):
                pass
                # paused = not paused
            elif k != -1:  # Next slide
                lcv.next_pic_time = lcv.cur_time

    if config.keyboard:
        pi3dfuncs.keyboard.close()
    pic_loading_proc.join()
    # TODO move display destroy etc to pi3dfuncs function
    pi3dfuncs._display.destroy()
    db.close()


if __name__ == "__main__":
    main()
