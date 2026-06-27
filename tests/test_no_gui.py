from pathlib import Path
from unittest.mock import patch, MagicMock

import sys

from pipictureframe.picdb.PictureUpdater import update_pictures_in_db
from tests.pictures import create_real_picture

# The display loop is driven by Pi3dFuncs.display_loop_running(). With a mocked
# Pi3dFuncs that would return a truthy MagicMock forever, so the loop would spin
# until --total_runtime wall-clock seconds elapsed. Cap it instead so the loop
# exits after a handful of iterations and the test stays in the millisecond range.
MAX_LOOP_ITERATIONS = 5


def prepare_env(tmp_path: Path):
    create_real_picture(tmp_path, "pic1.jpg")
    create_real_picture(tmp_path, "pic2.jpg")
    create_real_picture(tmp_path, "pic3.jpg")
    create_real_picture(tmp_path, "pic4.jpg")


@patch(
    "pipictureframe.utils.Config.convert_to_absolute_path", return_value="dummy_string"
)
def test_basic_execution(mock1, tmp_path: Path):
    prepare_env(tmp_path)
    db_connection_str = f"sqlite:///{tmp_path.as_posix()}/picture_db.db"

    # Pre-populate the database synchronously. Otherwise the NextPictureManager
    # finds an empty database on start-up and sleeps 10s waiting for the
    # background loader before the display loop even begins.
    update_pictures_in_db(str(tmp_path), db_connection_str)

    sys.argv = [sys.argv[0]]
    sys.argv = sys.argv + [
        "-p=" + str(tmp_path),
        f"--db_connection_string={db_connection_str}",
        "--total_runtime=5",
        "--log_level=INFO",
        "--time_delay=5",
        "--fade_time=1",
        "--show_text=2",
        "--check_dir_tm=18",
    ]
    pi3d_module_mock = MagicMock()
    sys.modules["pipictureframe.pi3dfuncs"] = pi3d_module_mock
    pi3d_mock = MagicMock()
    pi3d_module_mock.Pi3dFuncs = pi3d_mock
    # Run a bounded number of loop iterations, then stop the display loop.
    pi3d_mock.return_value.display_loop_running.side_effect = [True] * (
        MAX_LOOP_ITERATIONS
    ) + [False]
    from pipictureframe.pipictureframe import main

    main()
