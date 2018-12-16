"""This is part of the Mouse Tracks Python application.
Source: https://github.com/Peter92/MouseTracks
"""
#Basic image functions that require minimal imports

from __future__ import absolute_import

from ..utils.compatibility import Message
from ..config.language import LANGUAGE
from ..utils.os import create_folder, split_folder_and_file


def save_image_to_folder(image, file_path):
    """Handle saving images with messages."""
    file_name = split_folder_and_file(file_path, force_file=True)[1]
    Message(LANGUAGE.strings['Generation']['ImageSaveStart'].format_custom(IMAGE_NAME=file_name, IMAGE_PATH=file_path))
    try:
        create_folder(file_path)
        image.save(file_path)
    except IOError as error:
        Message(LANGUAGE.strings['Generation']['ImageSaveFail'].format_custom(IMAGE_NAME=file_name, IMAGE_PATH=file_path, REASON=error))
    else:
        Message(LANGUAGE.strings['Generation']['ImageSaveEnd'].format_custom(IMAGE_NAME=file_name, IMAGE_PATH=file_path))