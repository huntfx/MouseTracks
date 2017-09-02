from __future__ import division, absolute_import
from PIL import Image

from core.image.keyboard import DrawKeyboard
from core.image.calculate import merge_resolutions, convert_to_rgb, arrays_to_heatmap, arrays_to_colour, calculate_gaussian_size
from core.image.colours import ColourRange, calculate_colour_map
from core.constants import UPDATES_PER_SECOND
from core.compatibility import get_items, _print
from core.config import CONFIG, _config_defaults
from core.constants import format_file_path
from core.export import ExportCSV
from core.files import load_program, format_name
from core.maths import round_int
from core.os import create_folder
from core.versions import VERSION


class ImageName(object):
    """Generate an image name using values defined in the config.
    
    Potential additions:
        Date formatting (eg. [j]-[M]-[Y])
        Inline if/else
    """
    
    # To do: Add date format strings to it, like [j]-[M]-[Y]
    ALTERNATIVES = {
        'Width': ['ResX', 'ResolutionX', 'ImageWidth', 'OutputWidth', 'X'],
        'Height': ['ResY', 'ResolutionY', 'ImageHeight', 'OutputHeight', 'Y'],
        'UpscaleWidth': ['UpscaleX', 'UpscaleResolutionX', 'UpscaleWidth', 'UWidth', 'UX'],
        'UpscaleHeight': ['UpscaleY', 'UpscaleResolutionY', 'UpscaleHeight', 'UHeight', 'UY'],
        'Exponential': ['ExponentialMultiplier', 'ExpMult'],
        'Colours': ['Colors', 'ColourMap', 'ColorMap', 'ColourProfile', 'ColorProfile'],
        'MouseButton': ['MouseButtons'],
        'FileName': ['FName'],
        'FirstSave': ['CTime', 'CreationTime', 'Created'], #1494809091
        'LatestSave': ['LastSave', 'MTime', 'ModifiedTime', 'LastModified'], #1503929321
        'RunningTimeSeconds': ['RTSeconds'],
        'RunningTimeMinutes': ['RTMinutes'],
        'RunningTimeHours': ['RTHours'],
        'RunningTimeDays': ['RTDays'],
        'Ticks': [],
        'FileVersion': [],
        'Version': [],
        'GaussianBlur': ['Gaussian', 'Blur', 'BlurAmount', 'GaussianSize'],
        'GaussianSigma': [],
        'RangeLimit': ['MaximumRange', 'MaximumValue', 'MaxRange', 'MaxValue', 'ValueLimit'],
        'DataSet': [],
        'Mapping': ['ColourMapping'],
        'Size': ['SizeMultiplier', 'SizeMult'],
        'Extended': ['ExtendedKeyboard'],
        'Sessions': ['NumSessions'],
        'HighPrecision': ['HighDetail']
    }
        
        
    def __init__(self, program_name, load_profile=False, data=None):
        self.name = program_name.replace('\\', '').replace('/', '')
        if data is None and load_profile:
            data = load_program(data)
        self.data = data
        self.file_name = format_name(self.name)
        self.reload()

    def reload(self):
        
        g_im = CONFIG['GenerateImages']
        g_hm = CONFIG['GenerateHeatmap']
        g_t = CONFIG['GenerateTracks']
        g_kb = CONFIG['GenerateKeyboard']
    
        #self.width = str(g_im['OutputResolutionX'])
        #self.height = str(g_im['OutputResolutionY'])
        self.width = str(g_im['_TempResolutionX'])
        self.height = str(g_im['_TempResolutionY'])
        self.uwidth = str(g_im['_UpscaleResolutionX'])
        self.uheight = str(g_im['_UpscaleResolutionY'])
        self.high_precision = 'High Detail' if g_im['HighPrecision'] else 'Normal'
        
        self.heatmap_exponential = str(g_hm['ExponentialMultiplier'])
        self.heatmap_colours = str(g_hm['ColourProfile'])
        self.heatmap_buttons = {'LMB': g_hm['_MouseButtonLeft'],
                                'MMB': g_hm['_MouseButtonMiddle'],
                                'RMB': g_hm['_MouseButtonRight']}
        selected_buttons = [k for k, v in get_items(self.heatmap_buttons) if v]
        if len(selected_buttons) == 3:
           self.heatmap_button_group = 'Combined'
        elif len(selected_buttons) == 2:
            self.heatmap_button_group = '+'.join(selected_buttons)
        elif len(selected_buttons) == 1:
            self.heatmap_button_group = selected_buttons[0]
        else:
            self.heatmap_button_group = 'Empty'
        self.heatmap_gaussian_actual = str(calculate_gaussian_size(g_im['_UpscaleResolutionX'], 
                                                                   g_im['_UpscaleResolutionY']))
        self.heatmap_gaussian = str(g_hm['GaussianBlurMultiplier'])
        self.heatmap_max = str(g_hm['ManualRangeLimit'])

        self.track_colour = str(g_t['ColourProfile'])

        self.keyboard_colour = str(g_kb['ColourProfile'])
        self.keyboard_set = g_kb['DataSet'][0].upper() + g_kb['DataSet'][1:].lower()
        self.keyboard_exponential = str(g_kb['ExponentialMultiplier'])
        self.keyboard_mapping = g_kb['ColourMapping'][0].upper() + g_kb['ColourMapping'][1:].lower()
        self.keyboard_size_mult = str(g_kb['SizeMultiplier'])
        self.keyboard_extended = 'Extended' if g_kb['ExtendedKeyboard'] else 'Compact'

    def generate(self, image_type, reload=False):
    
        image_type = image_type.lower()
    
        if reload:
            self.reload()
        
        lookup = {'clicks': 'GenerateHeatmap',
                  'tracks': 'GenerateTracks',
                  'keyboard': 'GenerateKeyboard',
                  'csv-tracks': 'NameFormatTracks',
                  'csv-clicks': 'NameFormatClicks',
                  'csv-keyboard': 'NameFormatKeyboard'}
        try:
            name = CONFIG[lookup[image_type]]['NameFormat']
        except KeyError:
            try:
                name = CONFIG['GenerateCSV'][lookup[image_type]]
            except KeyError:
                raise ValueError('incorred image type: {}'.format(image_type))
        
        #Rename alternative variables
        for k, v in get_items(self.ALTERNATIVES):
            k = '[{}]'.format(k)
            for i in v:
                i = '[{}]'.format(i)
                name = name.replace(i, k)
        
        #General Options
        name = name.replace('[Name]', self.name)
        name = name.replace('[FileName]', self.file_name)
        name = name.replace('[Width]', self.width)
        name = name.replace('[Height]', self.height)
        name = name.replace('[UpscaleWidth]', self.uwidth)
        name = name.replace('[UpscaleHeight]', self.uheight)
        name = name.replace('[Version]', VERSION)
        name = name.replace('[HighPrecision]', self.high_precision)
        
        if self.data is not None:
            name = name.replace('[FirstSave]', str(round_int(self.data['Time']['Created'])))
            name = name.replace('[LatestSave]', str(round_int(self.data['Time']['Modified'])))
            name = name.replace('[FileVersion]', str(self.data['Version']))
            name = name.replace('[TimesLoaded]', str(self.data['TimesLoaded']))
            name = name.replace('[Sessions]', str(len(self.data['SessionStarts'])))
            ticks = self.data['Ticks']['Total']
            name = name.replace('[Ticks]', str(int(ticks)))
            name = name.replace('[RunningTimeSeconds]', str(round_int(ticks / UPDATES_PER_SECOND)))
            name = name.replace('[RunningTimeMinutes]', str(round(ticks / (UPDATES_PER_SECOND * 60), 2)))
            name = name.replace('[RunningTimeHours]', str(round(ticks / (UPDATES_PER_SECOND * 60 * 60), 2)))
            name = name.replace('[RunningTimeDays]', str(round(ticks / (UPDATES_PER_SECOND * 60 * 60 * 24), 2)))
        
        #Specific options
        if image_type == 'clicks':
            name = name.replace('[Exponential]', self.heatmap_exponential)
            name = name.replace('[Colours]', self.heatmap_colours)
            name = name.replace('[MouseButton]', self.heatmap_button_group)
            name = name.replace('[GaussianBlur]', self.heatmap_gaussian)
            name = name.replace('[GaussianSigma]', self.heatmap_gaussian_actual)
            name = name.replace('[RangeLimit]', self.heatmap_max)
        
        elif image_type == 'tracks':
            name = name.replace('[Colours]', self.track_colour)
            
        elif image_type.lower() == 'keyboard':
            name = name.replace('[Exponential]', self.keyboard_exponential)
            name = name.replace('[Colours]', self.keyboard_colour)
            name = name.replace('[DataSet]', self.keyboard_set)
            name = name.replace('[Mapping]', self.keyboard_mapping)
            name = name.replace('[Size]', self.keyboard_size_mult)
            name = name.replace('[Extended]', self.keyboard_extended)
        
        elif image_type.startswith('csv'):
            if image_type == 'csv-clicks':
                
                #Using the heatmap mouse buttons saves rewriting parts of the function,
                #but the config will need edited first to only have one button selected.
                name = name.replace('[MouseButton]', self.heatmap_button_group)
            
        else:
            raise ValueError('incorred image type: {}'.format(image_type))
                
        #Replace invalid characters
        invalid_chars = ':*?"<>|'
        for char in invalid_chars:
            if char in name:
                name = name.replace(char, '')
                
        if image_type.startswith('csv'):
            ext = 'csv'
        else:
            ext = CONFIG['GenerateImages']['FileType']
        
        return '{}.{}'.format(format_file_path(name), ext)


class RenderImage(object):
    def __init__(self, profile, data=None):
        self.profile = profile
        if data is None:
            self.data = load_program(profile, _update_version=False)
        else:
            self.data = data
        self.name = ImageName(profile, data=self.data)

    def keys_per_hour(self, session=False):
        """Detect if the game has keyboard tracking or not.
        Based on my own tracks, a game may range from 100 to 4000 normally.
        Without keyboard tracking, it's generally between 0.01 and 5.
        Check if this number is above 10 or 20 to get an idea.
        """
        
        if session:
            all_clicks = self.data['Keys']['Session']['Held']
            ticks = self.data['Ticks']['Session']['Total']
        else:
            all_clicks = self.data['Keys']['All']['Held']
            ticks = self.data['Ticks']['Total']
            
        include = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 '
        total_presses = sum(v for k, v in get_items(all_clicks) if k in include)
        return 3600 * total_presses / ticks
        
    def csv(self):
        
        export = ExportCSV(self.profile, self.data)
        
        if CONFIG['GenerateCSV']['_GenerateTracks']:
            csv_name = self.name.generate('csv-tracks', reload=True)
            export.tracks(self.name)
            
        if CONFIG['GenerateCSV']['_GenerateClicks']:
            export.clicks(self.name)
            
        if CONFIG['GenerateCSV']['_GenerateKeyboard']:
            csv_name = self.name.generate('csv-keyboard', reload=True)
            export.keyboard(self.name)
            
        
    def generate(self, image_type, last_session=False, save_image=True):
        image_type = image_type.lower()
        if image_type not in ('tracks', 'clicks', 'keyboard'):
            raise ValueError('image type \'{}\' not supported'.format(image_type))
        
        
        if not self.data['Ticks']['Total']:
            image_output = None
        
        else:
        
            CONFIG['GenerateImages']['_TempResolutionX'] = CONFIG['GenerateImages']['OutputResolutionX']
            CONFIG['GenerateImages']['_TempResolutionY'] = CONFIG['GenerateImages']['OutputResolutionY']
            
            high_precision = CONFIG['GenerateImages']['HighPrecision']
            allow_resize = True
            
            #Generate mouse tracks image
            if image_type == 'tracks':
            
                session_start = self.data['Ticks']['Session']['Tracks'] if last_session else None
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
                if last_session:
                    clicks = self.data['Maps']['Session']['Clicks']
                else:
                    clicks = self.data['Maps']['Clicks']
                numpy_arrays = merge_resolutions(self.data['Maps']['Clicks'], multiple_selection=mb, 
                                                 _find_range=False, high_precision=False)
                
                _h, _w = numpy_arrays[0].shape
                gaussian_size = calculate_gaussian_size(_w, _h)

                (min_value, max_value), heatmap = arrays_to_heatmap(numpy_arrays,
                            gaussian_size=gaussian_size,
                            exponential_multiplier=CONFIG['GenerateHeatmap']['ExponentialMultiplier'])
                
                #Adjust range of heatmap            
                if CONFIG['GenerateHeatmap']['ManualRangeLimit']:
                    max_value = CONFIG['GenerateHeatmap']['ManualRangeLimit']
                    _print('Manually set highest range to {}'.format(max_value))
                else:
                    max_value *= CONFIG['GenerateHeatmap']['RangeLimitMultiplier']
                    CONFIG['GenerateHeatmap']['ManualRangeLimit'] = max_value
                
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
                create_folder(image_name)
                _print('Saving image...')
                image_output.save(image_name)
                _print('Finished saving.')
        return image_output
