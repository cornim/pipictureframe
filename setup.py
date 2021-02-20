import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="pipictureframe",
    version="0.10.11",
    packages=setuptools.find_packages(),
    include_package_data=True,
    url="https://github.com/cornim/pipictureframe",
    license="GPLv3",
    author="Dr. Cornelius Mund",
    author_email="",
    description="A program to use a raspberry pi with a monitor as a digital picture frame.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    scripts=["pi-picture-frame"],
    install_requires=[
        "pi3d>=2.41",
        "numpy>=1.19.5",
        "Pillow>=8.1.0",
        "geopy>=2.1.0",
        "sqlalchemy>=1.3.23",
        "python-dateutil>=2.8.1",
    ],
    classifiers=[
        "Development Status :: 4 - Beta",
        "Programming Language :: Python :: 3 :: Only",
        "License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)",
        "Operating System :: POSIX :: Linux",
    ],
)
