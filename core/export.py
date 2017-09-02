from __future__ import absolute_import

from core.compatibility import range, get_items, _print
from core.config import CONFIG
from core.files import load_program
from core.os import create_folder


class ExportCSV(object):
    def __init__(self, profile, data=None):
        if data is None:
            data = load_program(profile, _update_version=False)
        self.profile = profile
        self.data = data
    
    def _generate(self, resolution, data):
        
        if len(data) < CONFIG['GenerateCSV']['MinimumResPoints']:
            return None
        
        #Build list
        output = [['0'] * resolution[0] for _ in range(resolution[1])]
        for k, v in get_items(data):
            output[k[1]][k[0]] = str(v)
        
        #Add axis
        output_axis = [[''] + [str(i) for i in range(resolution[0])]]
        for i, row in enumerate(output):
            output_axis.append([str(i)] + row)
        
        return '\n'.join(','.join(row) for row in output)
   
    def tracks(self, image_name):
        
        _print('Generating CSV from tracks...')
        for resolution in self.data['Maps']['Tracks']:
            CONFIG['GenerateImages']['_TempResolutionX'], CONFIG['GenerateImages']['_TempResolutionY'] = resolution
            
            result = self._generate(resolution, self.data['Maps']['Tracks'][resolution])
            
            if result is not None:
                file_name = image_name.generate('csv-tracks', reload=True)
                create_folder(file_name)
                with open(file_name, 'w') as f:
                    f.write(result)
   
    def clicks(self, image_name):
        
        mouse_buttons = ['LMB', 'MMB', 'RMB']
        
        _print('Generating CSV from clicks...')
        for resolution in self.data['Maps']['Clicks']:
            CONFIG['GenerateImages']['_TempResolutionX'], CONFIG['GenerateImages']['_TempResolutionY'] = resolution
        
            for i, mb_clicks in enumerate(self.data['Maps']['Clicks'][resolution]):
                if mb_clicks:
                    
                    CONFIG['GenerateHeatmap']['_MouseButtonLeft'] = i == 0
                    CONFIG['GenerateHeatmap']['_MouseButtonMiddle'] = i == 1
                    CONFIG['GenerateHeatmap']['_MouseButtonRight'] = i == 2
        
                    result = self._generate(resolution, mb_clicks)
            
                    if result is not None:
                        file_name = image_name.generate('csv-clicks', reload=True)
                        create_folder(file_name)
                        with open(file_name, 'w') as f:
                            f.write(result)
    
    def keyboard(self, image_name):
        
        _print('Generating CSV from keyboard...')
        result = ['Key,Count,Time']
        for key in self.data['Keys']['All']['Pressed']:
            result.append('{},{},{}'.format(key, 
                                            self.data['Keys']['All']['Pressed'][key], 
                                            self.data['Keys']['All']['Held'][key]))
        
        file_name = image_name.generate('csv-keyboard', reload=True)
        create_folder(file_name)
        with open(file_name, 'w') as f:
            f.write('\n'.join(result))
