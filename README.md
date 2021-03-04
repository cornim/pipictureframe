# Pi Picture Frame

A picture frame script primarily developed for Raspberry
Pi but can also run under Linux.
(Some extra work is needed to run under Windows.)

It uses [pi3d](https://pi3d.github.io/) to render the pictures.
The actual OpenGL code is from [pi3d_demos](https://github.com/pi3d/pi3d_demos).

## Installation

```bash
sudo pip3 install pipictureframe
```

## Usage

Run

`pi-picture-frame -h`

to get a comprehensive list of options.
 
 ## Features
 
 - Smooth and configurable transitions from picture to 
 picture incl. pre-loading of next picture to avoid
 artifacts during transition
 - Probaility of picture selection based on the number of times
 it has been shown in the past
 - Background blurring
 - Image resizing
 - Configurable display of text (e.g. date, file name, etc.)
 - Caching of all picture files in db.
 - Filtering of image list
 
 ### Filters
 
 Currently only a filter based on image ratings is
 implemented. If additonal filters are needed, let me
 know. 
 