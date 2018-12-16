"""This is part of the Mouse Tracks Python application.
Source: https://github.com/Peter92/MouseTracks
"""
#Generate CSV files from data
#TODO: Not currently working or in use, needs fixing at some point

from __future__ import absolute_import

from ..utils import numpy
from ..utils.compatibility import range, iteritems, Message
from ..config.settings import CONFIG
from ..files import load_data
from ..config.language import LANGUAGE
from ..utils.os import create_folder


class ExportCSV(object):
    def __init__(self, profile, data=None):
        if data is None:
            data = load_data(profile, _update_version=False)
        self.profile = profile
        self.data = data
    
    def _generate(self, resolution, data):
        
        if numpy.count(data) < CONFIG['GenerateCSV']['MinimumPoints']:
            return None
        output = numpy.set_type(data, str)
        return '\n'.join(','.join(row) for row in output)
   
    def tracks(self, image_name):
        
        Message(LANGUAGE.strings['GenerationInput']['GenerateCSV'].format_custom(RENDER_TYPE='tracks'))
        for resolution in self.data['Maps']['Tracks']:
            CONFIG['GenerateImages']['_TempResolutionX'], CONFIG['GenerateImages']['_TempResolutionY'] = resolution
            
            result = self._generate(resolution, self.data['Maps']['Tracks'][resolution])
            if result is not None:
                file_name = image_name.generate('csv-tracks', reload=True)
                create_folder(file_name)
                with open(file_name, 'w') as f:
                    f.write(result)
   
    def clicks(self, image_name):
        
        Message(LANGUAGE.strings['GenerationInput']['GenerateCSV'].format_custom(RENDER_TYPE='clicks'))
        for i, mouse_button in enumerate(self.data['Maps']['Click']['Single']):
            CONFIG['GenerateHeatmap']['_MouseButtonLeft'] = i == 0
            CONFIG['GenerateHeatmap']['_MouseButtonMiddle'] = i == 1
            CONFIG['GenerateHeatmap']['_MouseButtonRight'] = i == 2
            
            for resolution, array in iteritems(self.data['Maps']['Click']['Single'][mouse_button]):
                CONFIG['GenerateImages']['_TempResolutionX'], CONFIG['GenerateImages']['_TempResolutionY'] = resolution
            
                result = self._generate(resolution, array)
                if result is not None:
                    file_name = image_name.generate('csv-clicks', reload=True)
                    create_folder(file_name)
                    with open(file_name, 'w') as f:
                        f.write(result)
            
        
    
    def keyboard(self, image_name):
        
        Message(LANGUAGE.strings['GenerationInput']['GenerateCSV'].format_custom(RENDER_TYPE='keyboard'))
        result = ['Key,Count,Time']
        for key in self.data['Keys']['All']['Pressed']:
            result.append('{},{},{}'.format(key, 
                                            self.data['Keys']['All']['Pressed'][key], 
                                            self.data['Keys']['All']['Held'][key]))
        
        file_name = image_name.generate('csv-keyboard', reload=True)
        create_folder(file_name)
        with open(file_name, 'w') as f:
            f.write('\n'.join(result))