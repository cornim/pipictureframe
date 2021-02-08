import locale
import logging
import math
import os

import numpy as np
from PIL import Image, ImageFilter

from pipictureframe.picdb.PictureUpdater import PictureData

log = logging.getLogger(__name__)

try:
    import pi3d
    from pi3d.Texture import MAX_SIZE
except ModuleNotFoundError as e:
    if "pygame" in e.msg:
        log.error(
            "Pygame must be installed manually if running on Windows. "
            'Please run "pip install pygame".'
        )
        exit(2)
    else:
        raise e


class Pi3dFuncs:
    def __init__(self, config):
        # noinspection PyBroadException
        try:
            locale.setlocale(locale.LC_TIME, config.local)
        except Exception as e:
            log.warning("error trying to set local to {}".format(config.local), e)

        self._display = pi3d.Display.create(
            x=config.display_x,
            y=config.display_y,
            w=config.display_w,
            h=config.display_h,
            frames_per_second=config.fps,
            display_config=pi3d.DISPLAY_CONFIG_HIDE_CURSOR,
            background=config.background,
        )
        self._camera = pi3d.Camera(is_3d=False)

        shader = pi3d.Shader(config.shader)
        self._slide = pi3d.Sprite(
            camera=self._camera, w=self._display.width, h=self._display.height, z=5.0
        )
        self._slide.set_shader(shader)
        self._slide.unif[47] = config.edge_alpha
        self._slide.unif[54] = config.blend_type
        self._slide.unif[55] = 1.0  # brightness used by shader [18][1]

        if config.keyboard:
            self.keyboard = pi3d.Keyboard()

        grid_size = math.ceil(len(config.codepoints) ** 0.5)
        font = pi3d.Font(
            config.font_file, codepoints=config.codepoints, grid_size=grid_size
        )
        self._text = pi3d.PointText(
            font, self._camera, max_chars=200, point_size=config.show_text_sz
        )
        self._textblock = pi3d.TextBlock(
            x=0,
            y=-self._display.height // 2 + (config.show_text_sz // 2) + 20,
            z=0.1,
            rot=0.0,
            char_count=199,
            text_format="{}".format(" "),
            size=0.99,
            spacing="F",
            justify=0.5,
            space=0.02,
            colour=(1.0, 1.0, 1.0, 1.0),
        )
        self._text.add_text_block(self._textblock)

        bkg_ht = self._display.height // 4
        text_bkg_array = np.zeros((bkg_ht, 1, 4), dtype=np.uint8)
        text_bkg_array[:, :, 3] = np.linspace(0, 170, bkg_ht).reshape(-1, 1)
        text_bkg_tex = pi3d.Texture(text_bkg_array, blend=True, free_after_load=True)
        self._text_bkg = pi3d.Plane(
            w=self._display.width,
            h=bkg_ht,
            y=-self._display.height // 2 + bkg_ht // 2,
            z=4.0,
        )
        back_shader = pi3d.Shader("uv_flat")
        self._text_bkg.set_draw_details(back_shader, [text_bkg_tex])

        self._foreground_slide = None
        self._background_slide = None

        # return display, camera, slide, keyboard, text_block, text, text_bkg

    @staticmethod
    def orientate_image(im, orientation):
        if orientation == 2:
            im = im.transpose(Image.FLIP_LEFT_RIGHT)
        elif orientation == 3:
            im = im.transpose(Image.ROTATE_180)  # rotations are clockwise
        elif orientation == 4:
            im = im.transpose(Image.FLIP_TOP_BOTTOM)
        elif orientation == 5:
            im = im.transpose(Image.FLIP_LEFT_RIGHT).transpose(Image.ROTATE_270)
        elif orientation == 6:
            im = im.transpose(Image.ROTATE_270)
        elif orientation == 7:
            im = im.transpose(Image.FLIP_LEFT_RIGHT).transpose(Image.ROTATE_90)
        elif orientation == 8:
            im = im.transpose(Image.ROTATE_90)
        return im

    def texture_load(self, picture: PictureData, config):
        size = (self._display.width, self._display.height)
        pic_path = picture.absolute_path
        orientation = picture.orientation

        try:
            im = Image.open(pic_path)

            (w, h) = im.size
            # changing MAX_SIZE causes serious crash on linux laptop!
            max_dimension = MAX_SIZE
            # turned off for 4K display - will cause issues on RPi before v4
            if not config.auto_resize:
                max_dimension = 3840  # TODO check if mipmapping should be turned off with this setting.
            if w > max_dimension:
                im = im.resize(
                    (max_dimension, int(h * max_dimension / w)), resample=Image.BICUBIC
                )
            elif h > max_dimension:
                im = im.resize(
                    (int(w * max_dimension / h), max_dimension), resample=Image.BICUBIC
                )
            if orientation > 1:
                im = Pi3dFuncs.orientate_image(im, orientation)
            if config.blur_edges and size is not None:
                wh_rat = (size[0] * im.height) / (size[1] * im.width)
                # make a blurred background if wh_rat is not exactly 1
                if abs(wh_rat - 1.0) > 0.01:
                    (sc_b, sc_f) = (size[1] / im.height, size[0] / im.width)
                    if wh_rat > 1.0:
                        (sc_b, sc_f) = (sc_f, sc_b)  # swap round
                    (w, h) = (
                        round(size[0] / sc_b / config.blur_zoom),
                        round(size[1] / sc_b / config.blur_zoom),
                    )
                    (x, y) = (round(0.5 * (im.width - w)), round(0.5 * (im.height - h)))
                    box = (x, y, x + w, y + h)
                    blr_sz = (int(x * 512 / size[0]) for x in size)
                    im_b = im.resize(size, resample=0, box=box).resize(blr_sz)
                    im_b = im_b.filter(ImageFilter.GaussianBlur(config.blur_amount))
                    im_b = im_b.resize(size, resample=Image.BICUBIC)
                    im_b.putalpha(
                        round(255 * config.edge_alpha)
                    )  # to apply the same EDGE_ALPHA as the no blur method.
                    im = im.resize(
                        (int(x * sc_f) for x in im.size), resample=Image.BICUBIC
                    )
                    """resize can use Image.LANCZOS (alias for Image.ANTIALIAS) for resampling
                    for better rendering of high-contranst diagonal lines. NB downscaled large
                    images are rescaled near the start of this try block if w or h > max_dimension
                    so those lines might need changing too.
                    """
                    im_b.paste(
                        im,
                        box=(
                            round(0.5 * (im_b.width - im.width)),
                            round(0.5 * (im_b.height - im.height)),
                        ),
                    )
                    im = im_b  # have to do this as paste applies in place
            tex = pi3d.Texture(
                im,
                blend=True,
                m_repeat=True,
                automatic_resize=config.auto_resize,
                free_after_load=True,
            )
            # tex = pi3d.Texture(im, blend=True, m_repeat=True, automatic_resize=config.AUTO_RESIZE,
            #                    mipmap=config.AUTO_RESIZE, free_after_load=True)
            # poss try this if still some artifacts with full resolution
        except Exception as e:
            log.error(f"Error loading file {pic_path}", e)
            tex = None
        return tex

    def load_fg(self, cur_pic: PictureData, config):
        self._foreground_slide = self.texture_load(cur_pic, config)
        wh_rat = (self._display.width * self._foreground_slide.iy) / (
            self._display.height * self._foreground_slide.ix
        )
        if (wh_rat > 1.0 and config.fit) or (wh_rat <= 1.0 and not config.fit):
            sz1, sz2, os1, os2 = 42, 43, 48, 49
        else:
            sz1, sz2, os1, os2 = 43, 42, 49, 48
            wh_rat = 1.0 / wh_rat
        self._slide.unif[sz1] = wh_rat
        self._slide.unif[sz2] = 1.0
        self._slide.unif[os1] = (wh_rat - 1.0) * 0.5
        self._slide.unif[os2] = 0.0

    def copy_fg_to_bg(self):
        self._background_slide = self._foreground_slide
        self._slide.unif[45:47] = self._slide.unif[
            42:44
        ]  # transfer front width and height factors to back
        self._slide.unif[51:53] = self._slide.unif[
            48:50
        ]  # transfer front width and height offsets

    # --- Sanitize the specified string by removing any chars not found in codepoints
    @staticmethod
    def sanitize_string(string, codepoints):
        return "".join([c for c in string if c in codepoints])

    @staticmethod
    def smooth_alpha(a):
        return a * a * (3.0 - 2.0 * a)

    def set_fg_bg_ratio(self, ratio):
        """
        Set ratio of foreground to background. 0 = only bg, 1 = only fg.
        """
        self._slide.unif[44] = self.smooth_alpha(ratio)

    def prepare_text(self, cur_pic: PictureData, config):
        string_components = []
        if config.show_text > 0:
            if (config.show_text & 1) == 1:  # name
                string_components.append(
                    self.sanitize_string(
                        os.path.basename(cur_pic.absolute_path), config.codepoints
                    )
                )
            if (config.show_text & 2) == 2:  # date
                string_components.append(
                    cur_pic.get_date_time().strftime(config.show_date_fm)
                )
            # TODO fix geoloc
            # if config.LOAD_GEOLOC and (config.SHOW_TEXT & 4) == 4:  # location
            #    loc_string = sanitize_string(iFiles[pic_num].location.strip())
            #    if loc_string:
            #        string_components.append(loc_string)
            if (config.show_text & 8) == 8:  # folder
                string_components.append(
                    self.sanitize_string(
                        os.path.basename(os.path.dirname(cur_pic.absolute_path)),
                        config.codepoints,
                    )
                )

            final_string = " • ".join(string_components)
            self._textblock.set_text(text_format=final_string, wrap=config.text_width)

            last_ch = len(final_string)
            adj_y = (
                self._text.locations[:last_ch, 1].min() + self._display.height // 2
            )  # y pos of last char rel to bottom of screen
            self._textblock.set_position(
                y=(self._textblock.y - adj_y + config.show_text_sz)
            )

        else:
            self._textblock.set_text(text_format=" ")
            self._textblock.colouring.set_colour(alpha=0.0)
            self._text_bkg.set_alpha(0.0)
        self._text.regen()

    def set_text_alpha_and_draw(self, alpha):
        alpha = self.smooth_alpha(alpha)
        self._textblock.colouring.set_colour(alpha=alpha)
        self._text.regen()
        self._text_bkg.set_alpha(alpha)
        self._text_bkg.draw()
        self._text.draw()

    def set_textures(self):
        self._slide.set_textures([self._foreground_slide, self._background_slide])

    def display_loop_running(self) -> bool:
        return self._display.loop_running()

    def draw_slide(self):
        self._slide.draw()
