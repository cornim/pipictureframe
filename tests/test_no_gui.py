from pathlib import Path
from unittest.mock import patch, MagicMock

import sys

from tests.pictures import create_real_picture


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
    sys.argv = [sys.argv[0]]
    sys.argv = sys.argv + [
        "-p=" + str(tmp_path),
        f"--db_connection_string=sqlite:///{tmp_path.as_posix()}/picture_db.db",
        "--total_runtime=25",
        "--log_level=INFO",
        "--time_delay=5",
        "--fade_time=1",
        "--show_text=2",
        "--check_dir_tm=18",
    ]
    pi3d_module_mock = MagicMock()
    sys.modules["pipictureframe.pi3dfuncs"] = pi3d_module_mock
    pi3d_mock = MagicMock()
    pi3d_module_mock.Pi3dFunc = pi3d_mock
    from pipictureframe.pipictureframe import main

    main()
