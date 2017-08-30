from __future__ import absolute_import

from core.compatibility import range, get_items
from core.files import load_program


class ExportCSV(object):
    def __init__(self, profile=None, data=None):
        if profile is None:
            if data is None:
                raise TypeError('profile name or data needs to be given')
        elif data is None:
            data = load_program(profile, _update_version=False)
        self.profile = profile
        self.data = data
    
    def _generate(self, resolution, data):
        output = [['0'] * resolution[0] for _ in range(resolution[1])]
        
        for k, v in get_items(data):
            output[k[1]][k[0]] = str(v)
        
        return '\n'.join(','.join(row) for row in output)
   
    def tracks(self, file_name):
        
        file_name = file_name.replace('[Name]', self.profile)
        
        for resolution in self.data['Maps']['Tracks']:
            result = self._generate(resolution, self.data['Maps']['Tracks'][resolution])
            
            res_name = file_name.replace('[Width]', str(resolution[0]))
            res_name = res_name.replace('[Height]', str(resolution[1]))
            with open(res_name, 'w') as f:
                f.write(result)
   
    def clicks(self, file_name):
        
        file_name = file_name.replace('[Name]', self.profile)
        
        mouse_buttons = ['LMB', 'MMB', 'RMB']
        
        for resolution in self.data['Maps']['Clicks']:
            for i, mb_clicks in enumerate(self.data['Maps']['Clicks'][resolution]):
                if mb_clicks:
                    result = self._generate(resolution, mb_clicks)
            
                    res_name = file_name.replace('[Width]', str(resolution[0]))
                    res_name = res_name.replace('[Height]', str(resolution[1]))
                    res_name = res_name.replace('[MouseButton]', mouse_buttons[i])
                    with open(res_name, 'w') as f:
                        f.write(result)
    
    def keys(self, file_name):
        
        file_name = file_name.replace('[Name]', self.profile)
        
        result = ['Key,Count,Time']
        for key in self.data['Keys']['All']['Pressed']:
            result.append('{},{},{}'.format(key, 
                                            self.data['Keys']['All']['Pressed'][key], 
                                            self.data['Keys']['All']['Held'][key]))
        
        with open(file_name, 'w') as f:
            f.write('\n'.join(result))
