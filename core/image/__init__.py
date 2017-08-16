from __future__ import division, absolute_import
from PIL import Image

from core.image.keyboard import DrawKeyboard
from core.image.calculate import merge_resolutions, convert_to_rgb, arrays_to_heatmap, arrays_to_colour
from core.image.colours import ColourRange, calculate_colour_map
from core.compatibility import get_items, _print
from core.config import CONFIG, _config_defaults
from core.constants import format_file_path
from core.files import load_program


class ImageName(object):
    """Generate an image name using values defined in the config.
    Not implemented yet: creation time | modify time | exe name
    """
    def __init__(self, program_name):
        self.name = program_name.replace('\\', '').replace('/', '')
        self.reload()

    def reload(self):
        self.output_res_x = str(CONFIG['GenerateImages']['OutputResolutionX'])
        self.output_res_y = str(CONFIG['GenerateImages']['OutputResolutionY'])
        self.upscale_res_x = str(CONFIG['GenerateImages']['_UpscaleResolutionX'])
        self.upscale_res_y = str(CONFIG['GenerateImages']['_UpscaleResolutionY'])

        self.heatmap_gaussian = str(CONFIG['GenerateHeatmap']['GaussianBlurSize'])
        self.heatmap_exp = str(CONFIG['GenerateHeatmap']['ExponentialMultiplier'])
        self.heatmap_colour = str(CONFIG['GenerateHeatmap']['ColourProfile'])
        self.heatmap_buttons = {'LMB': CONFIG['GenerateHeatmap']['_MouseButtonLeft'],
                                'MMB': CONFIG['GenerateHeatmap']['_MouseButtonMiddle'],
                                'RMB': CONFIG['GenerateHeatmap']['_MouseButtonRight']}

        self.track_colour = str(CONFIG['GenerateTracks']['ColourProfile'])

        self.keyboard_colour = str(CONFIG['GenerateKeyboard']['ColourProfile'])

    def generate(self, image_type, reload=False):
    
        if reload:
            self.reload()
            
        if image_type.lower() == 'clicks':
            name = CONFIG['GenerateHeatmap']['NameFormat']
            name = name.replace('[ExpMult]', self.heatmap_exp)
            name = name.replace('[GaussianSize]', self.heatmap_gaussian)
            name = name.replace('[ColourProfile]', self.heatmap_colour)
            
            selected_buttons = [k for k, v in get_items(self.heatmap_buttons) if v]
            if all(self.heatmap_buttons.values()):
                name = name.replace('[MouseButtons]', 'Combined')
            elif len(selected_buttons) == 2:
                name = name.replace('[MouseButtons]', '+'.join(selected_buttons))
            elif len(selected_buttons) == 1:
                name = name.replace('[MouseButtons]', selected_buttons[0])
            else:
                name = name.replace('[MouseButtons]', 'Empty')

        elif image_type.lower() == 'tracks':
            name = CONFIG['GenerateTracks']['NameFormat']
            name = name.replace('[ColourProfile]', self.track_colour)
            
        elif image_type.lower() == 'keyboard':
            name = CONFIG['GenerateKeyboard']['NameFormat']
            name = name.replace('[ColourProfile]', self.keyboard_colour)
        
        else:
            raise ValueError('incorred image type: {}, '
                             'must be tracks, clicks or keyboard'.format(image_type))
        name = name.replace('[UResX]', self.upscale_res_x)
        name = name.replace('[UResY]', self.upscale_res_y)
        name = name.replace('[ResX]', self.output_res_x)
        name = name.replace('[ResY]', self.output_res_y)
        name = name.replace('[Name]', self.name)

        #Replace invalid characters
        invalid_chars = ':*?"<>|'
        for char in invalid_chars:
            if char in name:
                name = name.replace(char, '')
        
        return '{}.{}'.format(format_file_path(name), CONFIG['GenerateImages']['FileType'])


class RenderImage(object):
    def __init__(self, profile, data=None):
        self.profile = profile
        if data is None:
            self.data = load_program(profile, _update_version=False)
        else:
            self.data = data
        self.name = ImageName(profile)

    def generate(self, image_type, last_session=False, save_image=True):
        image_type = image_type.lower()
        if image_type not in ('tracks', 'clicks', 'keyboard'):
            raise ValueError('image type \'{}\' not supported'.format(image_type))
        
        session_start = self.data['Ticks']['Session']['Current'] if last_session else None
        if not self.data['Ticks']['Total']:
            image_output = None
        
        else:
            
            high_precision = CONFIG['GenerateImages']['HighPrecision']
            allow_resize = True
            
            #Generate mouse tracks image
            if image_type == 'tracks':
                (min_value, max_value), numpy_arrays = merge_resolutions(self.data['Maps']['Tracks'], 
                                                                         session_start=session_start,
                                                                         high_precision=high_precision)
                try:
                    colour_map = calculate_colour_map(CONFIG['GenerateTracks']['ColourProfile'])
                except ValueError:
                    default_colours = _config_defaults['GenerateTracks']['ColourProfile'][0]
                    colour_map = calculate_colour_map(default_colours)
                colour_range = ColourRange(min_value, max_value, colour_map)
                image_output = arrays_to_colour(colour_range, numpy_arrays)
                image_name = self.name.generate('Tracks', reload=True)
            
            #Generate click heatmap image
            elif image_type == 'clicks':
                lmb = CONFIG['GenerateHeatmap']['_MouseButtonLeft']
                mmb = CONFIG['GenerateHeatmap']['_MouseButtonMiddle']
                rmb = CONFIG['GenerateHeatmap']['_MouseButtonRight']
                mb = [i for i, v in enumerate((lmb, mmb, rmb)) if v]
                clicks = self.data['Maps']['Clicks']
                numpy_arrays = merge_resolutions(self.data['Maps']['Clicks'], multiple_selection=mb, 
                                                 session_start=session_start, _find_range=False,
                                                 high_precision=high_precision)

                (min_value, max_value), heatmap = arrays_to_heatmap(numpy_arrays,
                            gaussian_size=CONFIG['GenerateHeatmap']['GaussianBlurSize'],
                            exponential_multiplier=CONFIG['GenerateHeatmap']['ExponentialMultiplier'])
                
                #Adjust range of heatmap            
                if CONFIG['GenerateHeatmap']['ForceMaximumValue']:
                    max_value = CONFIG['GenerateHeatmap']['ForceMaximumValue']
                    _print('Manually set highest range to {}'.format(max_value))
                else:
                    max_value *= CONFIG['GenerateHeatmap']['MaximumValueMultiplier']
                
                #Convert each point to an RGB tuple
                _print('Converting to RGB...')
                try:
                    colour_map = calculate_colour_map(CONFIG['GenerateHeatmap']['ColourProfile'])
                except ValueError:
                    default_colours = _config_defaults['GenerateHeatmap']['ColourProfile'][0]
                    colour_map = calculate_colour_map(default_colours)
                colour_range = ColourRange(min_value, max_value, colour_map)
                image_output = Image.fromarray(convert_to_rgb(heatmap, colour_range))
              
              
                image_name = self.name.generate('Clicks', reload=True)
            
            elif image_type == 'keyboard':
                allow_resize = False
                kb = DrawKeyboard(self.profile, self.data, last_session=last_session)
                image_output = kb.draw_image()
                image_name = self.name.generate('Keyboard', reload=True)
            
        resolution = (CONFIG['GenerateImages']['OutputResolutionX'],
                      CONFIG['GenerateImages']['OutputResolutionY'])
            
        if image_output is None:
            _print('No image data was found for type "{}"'.format(image_type))
        else:
            if allow_resize:
                image_output = image_output.resize(resolution, Image.ANTIALIAS)
            if save_image:
                _print('Saving image...')
                image_output.save(image_name)
                _print('Finished saving.')
        return image_output
