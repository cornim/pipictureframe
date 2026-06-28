import importlib
import sys
from unittest.mock import MagicMock, Mock

import pytest


@pytest.fixture
def slide_mod():
    """Import pipictureframe.pipictureframe with pi3d stubbed out.

    The module imports Pi3dFuncs from pipictureframe.pi3dfuncs, which pulls in
    pi3d (and ultimately an OpenGL/display stack) that is neither available nor
    needed for these headless logic tests. Replace the package with a mock for
    the duration of the test and restore the previous state afterwards.
    """
    saved_pi3d = sys.modules.get("pipictureframe.pi3dfuncs")
    saved_main = sys.modules.pop("pipictureframe.pipictureframe", None)
    sys.modules["pipictureframe.pi3dfuncs"] = MagicMock()
    try:
        yield importlib.import_module("pipictureframe.pipictureframe")
    finally:
        if saved_pi3d is not None:
            sys.modules["pipictureframe.pi3dfuncs"] = saved_pi3d
        else:
            sys.modules.pop("pipictureframe.pi3dfuncs", None)
        sys.modules.pop("pipictureframe.pipictureframe", None)
        if saved_main is not None:
            sys.modules["pipictureframe.pipictureframe"] = saved_main


def _npm_returning(pics):
    npm = Mock()
    npm.get_next_picture = Mock(side_effect=list(pics))
    return npm


class TestLoadFgWithRetry:
    def test_returns_first_decodable_picture(self, slide_mod):
        pi3dfuncs = Mock()
        # Fail twice, then succeed on the third candidate.
        pi3dfuncs.load_fg = Mock(side_effect=[False, False, True])
        npm = _npm_returning(["a", "b", "c", "d"])
        result = slide_mod.load_fg_with_retry(pi3dfuncs, npm, Mock())
        assert result == "c"
        assert pi3dfuncs.load_fg.call_count == 3

    def test_returns_none_when_nothing_decodes(self, slide_mod):
        pi3dfuncs = Mock()
        pi3dfuncs.load_fg = Mock(return_value=False)
        npm = _npm_returning(range(slide_mod.MAX_LOAD_ATTEMPTS + 5))
        result = slide_mod.load_fg_with_retry(pi3dfuncs, npm, Mock())
        assert result is None
        assert pi3dfuncs.load_fg.call_count == slide_mod.MAX_LOAD_ATTEMPTS


class TestLoadNextSlide:
    def test_returns_new_picture_on_success(self, slide_mod):
        pi3dfuncs = Mock()
        pi3dfuncs.load_fg = Mock(return_value=True)
        npm = _npm_returning(["new"])
        result = slide_mod.load_next_slide(pi3dfuncs, npm, Mock(), "current")
        assert result == "new"
        pi3dfuncs.copy_fg_to_bg.assert_called_once()
        pi3dfuncs.set_textures.assert_called_once()

    def test_keeps_current_picture_when_load_fails(self, slide_mod):
        pi3dfuncs = Mock()
        pi3dfuncs.load_fg = Mock(return_value=False)
        npm = _npm_returning(range(slide_mod.MAX_LOAD_ATTEMPTS))
        result = slide_mod.load_next_slide(pi3dfuncs, npm, Mock(), "current")
        # Falls back to the current picture instead of returning None.
        assert result == "current"
        pi3dfuncs.set_textures.assert_called_once()
