"""
This is part of the Mouse Tracks Python application.
Source: https://github.com/Peter92/MouseTracks
"""
#This file contains basic functions for images that don't require image imports

from __future__ import absolute_import

from core.compatibility import Message
from core.language import STRINGS
from core.os import create_folder, split_folder_and_file


def save_image_to_folder(image, file_path):
    """Handle saving images with messages."""
    file_name = split_folder_and_file(file_path, force_file=True)[1]
    Message(STRINGS['Generation']['ImageSaveStart'].format_custom(IMAGE_NAME=file_name, IMAGE_PATH=file_path))
    try:
        create_folder(file_path)
        image.save(file_path)
    except IOError as error:
        Message(STRINGS['Generation']['ImageSaveFail'].format_custom(IMAGE_NAME=file_name, IMAGE_PATH=file_path, REASON=error))
    else:
        Message(STRINGS['Generation']['ImageSaveEnd'].format_custom(IMAGE_NAME=file_name, IMAGE_PATH=file_path))