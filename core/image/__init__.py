from __future__ import division, absolute_import
from PIL import Image
import zlib

from core.image.keyboard import DrawKeyboard
from core.image.calculate import merge_resolutions, convert_to_rgb, arrays_to_heatmap, arrays_to_colour, gaussian_size
from core.image.colours import ColourRange, calculate_colour_map
from core.constants import UPDATES_PER_SECOND
from core.compatibility import get_items, _print, pickle
from core.config import CONFIG, _config_defaults
from core.constants import format_file_path
from core.export import ExportCSV
from core.files import load_data, format_name
from core.maths import round_int
from core.os import create_folder, remove_file
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
        'Exponential': ['ExponentialMultiplier', 'ExpMult', 'Power', 'LinearPower'],
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
            data = load_data(data)
        self.data = data
        self.file_name = format_name(self.name)
        self.reload()

    def reload(self):
        
        g_im = CONFIG['GenerateImages']
        g_hm = CONFIG['GenerateHeatmap']
        g_t = CONFIG['GenerateTracks']
        g_kb = CONFIG['GenerateKeyboard']
    
        self.width = str(g_im['_TempResolutionX'])
        self.height = str(g_im['_TempResolutionY'])
        self.uwidth = str(g_im['_UpscaleResolutionX'])
        self.uheight = str(g_im['_UpscaleResolutionY'])
        self.high_precision = 'High Detail' if g_im['HighPrecision'] else 'Normal'
        
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
        self.heatmap_gaussian_actual = str(gaussian_size(g_im['_UpscaleResolutionX'], 
                                                                   g_im['_UpscaleResolutionY']))
        self.heatmap_gaussian = str(g_hm['GaussianBlurMultiplier'])

        self.track_colour = str(g_t['ColourProfile'])

        self.keyboard_colour = str(g_kb['ColourProfile'])
        self.keyboard_set = g_kb['DataSet'][0].upper() + g_kb['DataSet'][1:].lower()
        self.keyboard_exponential = str(g_kb['LinearPower'])
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
            name = name.replace('[Colours]', self.heatmap_colours)
            name = name.replace('[MouseButton]', self.heatmap_button_group)
            name = name.replace('[GaussianBlur]', self.heatmap_gaussian)
            name = name.replace('[GaussianSigma]', self.heatmap_gaussian_actual)
        
        elif image_type == 'tracks':
            name = name.replace('[Colours]', self.track_colour)
            
        elif image_type.lower() == 'keyboard':
            name = name.replace('[Exponential]', self.keyboard_exponential)
            name = name.replace('[Colours]', self.keyboard_colour)
            name = name.replace('[DataSet]', self.keyboard_set)
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
    def __init__(self, profile, data=None, allow_save=True):
        self.profile = profile
        if data is None:
            self.data = load_data(profile, _update_version=False, _create_new=False)
            if self.data is None:
                raise ValueError('profile doesn\'t exist')
        else:
            self.data = data
            
        self.name = ImageName(profile, data=self.data)
        self.save = allow_save

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
        
        #TODO: Option to only return file
        export = ExportCSV(self.profile, self.data)
        
        if CONFIG['GenerateCSV']['_GenerateTracks']:
            export.tracks(self.name)
            
        if CONFIG['GenerateCSV']['_GenerateClicks']:
            export.clicks(self.name)
            
        if CONFIG['GenerateCSV']['_GenerateKeyboard']:
            export.keyboard(self.name)
    
    def _generate_start(self):
        CONFIG['GenerateImages']['_TempResolutionX'] = CONFIG['GenerateImages']['OutputResolutionX']
        CONFIG['GenerateImages']['_TempResolutionY'] = CONFIG['GenerateImages']['OutputResolutionY']
    
    def _generate_end(self, image_name, image_output, resize=True):
        resolution = (CONFIG['GenerateImages']['OutputResolutionX'],
                      CONFIG['GenerateImages']['OutputResolutionY'])
            
        
        if resize:
            image_output = image_output.resize(resolution, Image.ANTIALIAS)
        if self.save:
            create_folder(image_name)
            _print('Saving image to "{}"...'.format(image_name))
            image_output.save(image_name)
            _print('Finished saving.')
            
        return image_output
    
    def cache_load(self, file_name):
        if file_name is None:
            return None
        _print('Loading from cache...')
        try:
            with open(file_name, 'rb') as f:
                return pickle.loads(zlib.decompress(f.read()))
        except IOError:
            return None
    
    def cache_save(self, file_name, min_value, max_value, array):
        _print('Saving to cache...')
        data = ((min_value, max_value), array)
        with open(file_name, 'wb') as f:
            f.write(zlib.compress(pickle.dumps(data)))
    
    def cache_delete(self, file_name):
        remove_file(file_name)
    
    def tracks(self, last_session=False, _cache_file=None):
        """Generate the track image."""
        self._generate_start()
        
        #Attempt to load data from cache
        cache_data = self.cache_load(_cache_file)
        if cache_data is not None:
            (min_value, max_value), numpy_arrays = cache_data
        skip_calculations = cache_data is not None
        
        if not skip_calculations:
        
            #Detect session information
            if last_session:
                session_start = self.data['Ticks']['Session']['Tracks']
            else:
                session_start = None
            
            #Resize all arrays
            high_precision = CONFIG['GenerateImages']['HighPrecision']
            (min_value, max_value), numpy_arrays = merge_resolutions(self.data['Maps']['Tracks'], 
                                                                     session_start=session_start,
                                                                     high_precision=high_precision)
        
        #Save cache if it wasn't generated
        if _cache_file is not None and not skip_calculations:
            self.cache_save(_cache_file, min_value, max_value, numpy_arrays)
        
        #Convert each point to an RGB tuple
        try:
            colour_map = calculate_colour_map(CONFIG['GenerateTracks']['ColourProfile'])
        except ValueError:
            default_colours = _config_defaults['GenerateTracks']['ColourProfile'][0]
            colour_map = calculate_colour_map(default_colours)
        colour_range = ColourRange(min_value, max_value, colour_map)
        
        image_name = self.name.generate('Tracks', reload=True)
        image_output = arrays_to_colour(colour_range, numpy_arrays)
        if image_output is None:
            _print('No tracks data was found.')
            return None
            
        return self._generate_end(image_name, image_output, resize=True)
    
    def doubleclicks(self, last_session=False, _cache_file=None):
        """Generate the double click image."""
        return self.clicks(last_session, 'Double', _cache_file=_cache_file)
    
    
    def clicks(self, last_session=False, click_type='Single', _cache_file=None):
        """Generate the click image."""
        self._generate_start()
        
        #Attempt to load data from cache
        cache_data = self.cache_load(_cache_file)
        if cache_data is not None:
            (min_value, max_value), heatmap = cache_data
        skip_calculations = cache_data is not None
        
        if not skip_calculations:
        
            #Detect session information
            if last_session:
                clicks = self.data['Maps']['Session']['Click'][click_type]
            else:
                clicks = self.data['Maps']['Click'][click_type]
        
            lmb = CONFIG['GenerateHeatmap']['_MouseButtonLeft']
            mmb = CONFIG['GenerateHeatmap']['_MouseButtonMiddle']
            rmb = CONFIG['GenerateHeatmap']['_MouseButtonRight']
            valid_buttons = [i for i, v in zip(('Left', 'Middle', 'Right'), (lmb, mmb, rmb)) if v]
            
            numpy_arrays = merge_resolutions(clicks, map_selection=valid_buttons)[1]
            
            width, height = CONFIG['GenerateImages']['_UpscaleResolutionX'], CONFIG['GenerateImages']['_UpscaleResolutionY']
            (min_value, max_value), heatmap = arrays_to_heatmap(numpy_arrays,
                        gaussian_size=gaussian_size(width, height),
                        clip=1-CONFIG['Advanced']['HeatmapRangeClipping'])
        
        #Save cache if it wasn't generated
        if _cache_file is not None and not skip_calculations:
            self.cache_save(_cache_file, min_value, max_value, heatmap)
            
        #Convert each point to an RGB tuple
        try:
            colour_map = calculate_colour_map(CONFIG['GenerateHeatmap']['ColourProfile'])
        except ValueError:
            default_colours = _config_defaults['GenerateHeatmap']['ColourProfile'][0]
            colour_map = calculate_colour_map(default_colours)
        colour_range = ColourRange(min_value, max_value, colour_map)
        
        image_name = self.name.generate('Clicks', reload=True)
        image_output = Image.fromarray(convert_to_rgb(heatmap, colour_range))
        
        if image_output is None:
            _print('No click data was found.')
            return None
            
        return self._generate_end(image_name, image_output, resize=True)
    
    def keyboard(self, last_session=False):
        """Generate the keyboard image."""
        kb = DrawKeyboard(self.profile, self.data, last_session=last_session)
        
        image_output = kb.draw_image()
        image_name = self.name.generate('Keyboard', reload=True)
        
        return self._generate_end(image_name, image_output, resize=False)
