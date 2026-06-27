from pipictureframe.utils.Config import (
    Config,
    parse_show_text,
    str_to_tuple,
    setup_parser,
)


class TestParseShowText:
    def test_empty_string_returns_zero(self):
        assert parse_show_text("") == 0

    def test_individual_bits(self):
        assert parse_show_text("name") == 1
        assert parse_show_text("date") == 2
        assert parse_show_text("location") == 4
        assert parse_show_text("folder") == 8

    def test_combination_is_bitwise_or(self):
        assert parse_show_text("name date folder") == 1 | 2 | 8

    def test_is_case_insensitive(self):
        assert parse_show_text("NAME Date") == 1 | 2


class TestStrToTuple:
    def test_parses_parenthesised_floats(self):
        assert str_to_tuple("(0.2, 0.2, 0.3, 1.0)") == (0.2, 0.2, 0.3, 1.0)

    def test_parses_without_parentheses(self):
        assert str_to_tuple("1,2,3") == (1.0, 2.0, 3.0)


class TestConfig:
    def _config(self, argv):
        args = setup_parser().parse_args(argv)
        return Config(args)

    def test_defaults(self):
        config = self._config([])
        assert config.time_delay == 8.0
        assert config.fade_time == 1.0
        assert config.fps == 20.0
        assert config.blend_type == 0.0  # "blend"
        assert config.min_rating is None
        assert config.max_rating is None
        assert config.shuffle is False
        # default --show_text is "date folder location" -> 2 | 8 | 4
        assert config.show_text == 2 | 4 | 8

    def test_blend_type_is_mapped_to_shader_constant(self):
        assert self._config(["--blend_type", "burn"]).blend_type == 1.0
        assert self._config(["--blend_type", "bump"]).blend_type == 2.0

    def test_blur_zoom_is_clamped_to_at_least_one(self):
        assert self._config(["--blur_zoom", "0.5"]).blur_zoom == 1.0
        assert self._config(["--blur_zoom", "2.0"]).blur_zoom == 2.0

    def test_delta_alpha_depends_on_fps_and_fade_time(self):
        config = self._config(["--fps", "10", "--fade_time", "2"])
        assert config.delta_alpha == 1.0 / (10.0 * 2.0)

    def test_rating_filters_and_shuffle_flags(self):
        config = self._config(["--min_rating", "2", "--max_rating", "4", "--shuffle"])
        assert config.min_rating == 2
        assert config.max_rating == 4
        assert config.shuffle is True

    def test_font_and_shader_resolve_to_bundled_resources(self):
        config = self._config([])
        assert config.font_file is not None
        assert config.font_file.endswith("NotoSans-Regular.ttf")
        # The ".fs" extension added before resolving is stripped back off.
        assert config.shader.endswith("blend_new")
