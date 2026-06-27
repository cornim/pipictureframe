from hashlib import md5

from pipictureframe.utils.PictureReader import PictureFile, HASH_CHUNK_SIZE


class TestPictureHash:
    def _write(self, path, content):
        path.write_bytes(content)
        return content

    def test_hash_small_file(self, tmp_path):
        path = tmp_path / "small.jpg"
        content = self._write(path, b"hello world")
        expected = md5(content).hexdigest()
        assert PictureFile(str(path)).hash == expected

    def test_hash_file_larger_than_chunk(self, tmp_path):
        # Spans several chunks plus a partial trailing chunk to exercise the
        # chunk boundary handling.
        path = tmp_path / "big.jpg"
        content = self._write(path, b"\xde\xad\xbe\xef" * (HASH_CHUNK_SIZE))
        expected = md5(content).hexdigest()
        assert PictureFile(str(path)).hash == expected

    def test_hash_empty_file(self, tmp_path):
        path = tmp_path / "empty.jpg"
        content = self._write(path, b"")
        expected = md5(content).hexdigest()
        assert PictureFile(str(path)).hash == expected
