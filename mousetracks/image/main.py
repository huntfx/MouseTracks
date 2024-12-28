"""This is part of the Mouse Tracks Python application.
Source: https://github.com/Peter92/MouseTracks
"""
#Group the other image functions into an easy to use file

from __future__ import absolute_import, division

from PIL import Image
import zlib

from .export import ExportCSV
from .misc import save_image_to_folder
from .calculate import arrays_to_heatmap, arrays_to_colour, gaussian_size, calculate_resolution, upscale_arrays_to_resolution
from .colours import ColourRange, calculate_colour_map
from .keyboard import DrawKeyboard
from ..config.language import LANGUAGE
from ..config.settings import CONFIG
from ..misc import format_file_path
from ..constants import UPDATES_PER_SECOND, DEFAULT_NAME
from ..files import LoadData, format_name
from ..utils.compatibility import Message, pickle, iteritems
from ..utils.maths import round_int
from ..utils.os import remove_file, join_path
from ..versions import VERSION


class ImageName(object):
    """Generate an image name using values defined in the config.
    
    Potential additions:
        Date formatting (eg. [j]-[M]-[Y])
        Inline if/else
        
    TODO: Full rewrite. It works but is way too messy.
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
        if program_name is None:
            program_name = DEFAULT_NAME
        self.name = program_name.replace('\\', '').replace('/', '')
        if data is None and load_profile:
            data = LoadData(data)
        self.data = data
        self.file_name = format_name(self.name)
        self.reload()

    def reload(self):
        
        g_im = CONFIG['GenerateImages']
        g_hm = CONFIG['GenerateHeatmap']
        g_t = CONFIG['GenerateTracks']
        g_sp = CONFIG['GenerateSpeed']
        g_st = CONFIG['GenerateStrokes']
        g_kb = CONFIG['GenerateKeyboard']
    
        self.width = str(g_im['_OutputResolutionX'])
        self.height = str(g_im['_OutputResolutionY'])
        self.uwidth = str(g_im['_UpscaleResolutionX'])
        self.uheight = str(g_im['_UpscaleResolutionY'])
        self.high_precision = 'High Detail' if g_im['HighPrecision'] else 'Normal'
        
        self.heatmap_colours = str(g_hm['ColourProfile'])
        self.heatmap_buttons = {'LMB': g_hm['_MouseButtonLeft'],
                                'MMB': g_hm['_MouseButtonMiddle'],
                                'RMB': g_hm['_MouseButtonRight']}
        selected_buttons = [k for k, v in iteritems(self.heatmap_buttons) if v]
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
        
        self.speed_colour = str(g_sp['ColourProfile'])
        
        self.stroke_colour = str(g_st['ColourProfile'])

        self.keyboard_colour = str(g_kb['ColourProfile'])
        self.keyboard_set = g_kb['DataSet'][0].upper() + g_kb['DataSet'][1:].lower()
        self.keyboard_exponential = str(g_kb['LinearPower'])
        self.keyboard_size_mult = str(g_kb['SizeMultiplier'])
        self.keyboard_extended = 'Extended' if g_kb['ExtendedKeyboard'] else 'Compact'

    def generate(self, image_type=None, reload=False):
        """Generate and format a folder/image path."""
        name = self._generate(image_type=image_type, reload=reload)
        
        #Replace invalid characters
        invalid_chars = ':*?"<>|'
        for char in invalid_chars:
            if char in name:
                name = name.replace(char, '')
        
        return format_file_path(name)
        
    def _generate(self, image_type=None, reload=False):
        
        if image_type is not None:
            image_type = image_type.lower()
    
        if reload:
            self.reload()
        
        #Lookup the name in the config file
        lookup = {'clicks': 'GenerateHeatmap',
                  'tracks': 'GenerateTracks',
                  'speed': 'GenerateSpeed',
                  'strokes': 'GenerateStrokes',
                  'keyboard': 'GenerateKeyboard',
                  'csv-tracks': 'FileNameTracks',
                  'csv-clicks': 'FileNameClicks',
                  'csv-keyboard': 'FileNameKeyboard'}
        try:
            name = CONFIG[lookup[image_type]]['FileName']
            
        #CSV follows a different format, so if no match, try CSV
        except KeyError:
            try:
                name = CONFIG['GenerateCSV'][lookup[image_type]]
            except KeyError:
                if image_type is not None:
                    raise ValueError('incorred image type: {}'.format(image_type))
                name = ''
        
        name = join_path((CONFIG['Paths']['Images'], name))
        
        #Rename alternative variables
        for k, v in iteritems(self.ALTERNATIVES):
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
            name = name.replace('[Sessions]', str(len(self.data['Sessions'])))
            ticks = self.data['Ticks']['Total']
            name = name.replace('[Ticks]', str(int(ticks)))
            name = name.replace('[RunningTimeSeconds]', str(round_int(ticks / UPDATES_PER_SECOND)))
            name = name.replace('[RunningTimeMinutes]', str(round(ticks / (UPDATES_PER_SECOND * 60), 2)))
            name = name.replace('[RunningTimeHours]', str(round(ticks / (UPDATES_PER_SECOND * 60 * 60), 2)))
            name = name.replace('[RunningTimeDays]', str(round(ticks / (UPDATES_PER_SECOND * 60 * 60 * 24), 2)))
        
        if image_type is None:
            return name
        
        #Specific options
        if image_type == 'clicks':
            name = name.replace('[Colours]', self.heatmap_colours)
            name = name.replace('[MouseButton]', self.heatmap_button_group)
            name = name.replace('[GaussianBlur]', self.heatmap_gaussian)
            name = name.replace('[GaussianSigma]', self.heatmap_gaussian_actual)
        
        elif image_type == 'tracks':
            name = name.replace('[Colours]', self.track_colour)
            
        elif image_type == 'speed':
            name = name.replace('[Colours]', self.speed_colour)
            
        elif image_type == 'strokes':
            name = name.replace('[Colours]', self.stroke_colour)
            
        elif image_type == 'keyboard':
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
                
        if image_type.startswith('csv'):
            ext = 'csv'
        else:
            ext = CONFIG['GenerateImages']['FileType']
        
        return '{}.{}'.format(name, ext)


class RenderImage(object):
    
    def __init__(self, profile=None, allow_save=True):
    
        if isinstance(profile, LoadData):
            self.profile = profile.name
            self.data = profile
        else:
            self.profile = profile
        
            self.data = LoadData(profile, _update_metadata=False)
            if self.data is None:
                raise ValueError('profile doesn\'t exist')
            
        self.name = ImageName(self.profile, data=self.data)
        self.save = allow_save

    def keys_per_hour(self, session=False):
        """Detect if the game has keyboard tracking or not.
        This is for if the script is not elevated while running.
        
        Based on my own tracks, a game may range from 100 to 4000 normally.
        Without keyboard tracking, it's generally between 0.01 and 5.
        """
        
        if session:
            all_clicks = self.data['Keys']['Session']['Held']
            ticks = self.data['Ticks']['Session']['Total']
        else:
            all_clicks = self.data['Keys']['All']['Held']
            ticks = self.data['Ticks']['Total']
        
        if not ticks:
            return 0
        
        total_presses = sum(v for k, v in iteritems(all_clicks) if k in (ord(i) for i in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 '))
        return 3600 * total_presses / ticks
        
    def csv(self):
        """Export data as CSV files."""
        export = ExportCSV(self.profile, self.data)
        
        if CONFIG['GenerateCSV']['_GenerateTracks']:
            export.tracks(self.name)
            
        if CONFIG['GenerateCSV']['_GenerateClicks']:
            export.clicks(self.name)
            
        if CONFIG['GenerateCSV']['_GenerateKeyboard']:
            export.keyboard(self.name)

    def _get_colour_range(self, min_value, max_value, config_heading, custom_map=None):
        """Get the colour range for the chosen config heading,
        or revert back to the default one if it is invalid.
        """
        try:
            colour_map = calculate_colour_map(CONFIG[config_heading]['ColourProfile'])
        except ValueError:
            try:
                colour_map = calculate_colour_map(CONFIG[config_heading]['ColourProfile'].default)
            except ValueError:
                if custom_map is None:
                    raise
                colour_map = calculate_colour_map(custom_map)
        return ColourRange(min_value, max_value, colour_map)
    
    def tracks(self, last_session=False, file_path=None, colour_override=None):
        """Render track image."""
        track_data = self.data.get_tracks()
        if track_data is None:
            Message(LANGUAGE.strings['Generation']['NoData'])
            return None
            
        top_resolution, (min_value, max_value), tracks = track_data
        
        output_resolution, upscale_resolution = calculate_resolution(tracks.keys(), top_resolution)
        upscaled_arrays = upscale_arrays_to_resolution(tracks, upscale_resolution)

        colour_range = self._get_colour_range(min_value, max_value, 'GenerateTracks', custom_map=colour_override)
        
        image_output = arrays_to_colour(colour_range, upscaled_arrays)
        image_output = image_output.resize(output_resolution, Image.LANCZOS)

        if file_path is None:
            file_path = self.name.generate('Tracks', reload=True)
            
        if self.save:
            save_image_to_folder(image_output, file_path)
    
    def speed(self, last_session=False, file_path=None, colour_override=None):
        """Render speed track image."""
    
        track_data = self.data.get_speed()
        if track_data is None:
            Message(LANGUAGE.strings['Generation']['NoData'])
            return None
            
        top_resolution, (min_value, max_value), tracks = track_data
        
        output_resolution, upscale_resolution = calculate_resolution(tracks.keys(), top_resolution)
        upscaled_arrays = upscale_arrays_to_resolution(tracks, upscale_resolution)

        colour_range = self._get_colour_range(min_value, max_value, 'GenerateSpeed', custom_map=colour_override)
        
        image_output = arrays_to_colour(colour_range, upscaled_arrays)
        image_output = image_output.resize(output_resolution, Image.LANCZOS)

        if file_path is None:
            file_path = self.name.generate('Speed', reload=True)
            
        if self.save:
            save_image_to_folder(image_output, file_path)
    
    def strokes(self, last_session=False, file_path=None, colour_override=None):
        """Render brush strokes image."""
    
        track_data = self.data.get_strokes()
        if track_data is None:
            Message(LANGUAGE.strings['Generation']['NoData'])
            return None
            
        top_resolution, (min_value, max_value), tracks = track_data
        
        output_resolution, upscale_resolution = calculate_resolution(tracks.keys(), top_resolution)
        upscaled_arrays = upscale_arrays_to_resolution(tracks, upscale_resolution)

        colour_range = self._get_colour_range(min_value, max_value, 'GenerateStrokes', custom_map=colour_override)
        
        image_output = arrays_to_colour(colour_range, upscaled_arrays)
        image_output = image_output.resize(output_resolution, Image.LANCZOS)

        if file_path is None:
            file_path = self.name.generate('Strokes', reload=True)
            
        if self.save:
            save_image_to_folder(image_output, file_path)

    def double_clicks(self, last_session=False, file_path=None, colour_override=None):
        """Render heatmap of double clicks."""
        return self.clicks(last_session=last_session, file_path=file_path, colour_override=colour_override, _double_click=True)

    def clicks(self, last_session=False, file_path=None, colour_override=None, _double_click=False):
        """Render heatmap of clicks."""

        top_resolution, (min_value, max_value), clicks = self.data.get_clicks(session=last_session, double_click=_double_click)
        output_resolution, upscale_resolution = calculate_resolution(clicks.keys(), top_resolution)

        lmb = CONFIG['GenerateHeatmap']['_MouseButtonLeft']
        mmb = CONFIG['GenerateHeatmap']['_MouseButtonMiddle']
        rmb = CONFIG['GenerateHeatmap']['_MouseButtonRight']
        skip = []
        if lmb or mmb or rmb:
            if not lmb:
                skip.append(0)
            if not mmb:
                skip.append(1)
            if not rmb:
                skip.append(2)
        upscaled_arrays = upscale_arrays_to_resolution(clicks, upscale_resolution, skip=skip)

        (min_value, max_value), heatmap = arrays_to_heatmap(upscaled_arrays,
                               gaussian_size=gaussian_size(upscale_resolution[0], upscale_resolution[1]),
                               clip=1-CONFIG['Advanced']['HeatmapRangeClipping'])

        colour_range = self._get_colour_range(min_value, max_value, 'GenerateHeatmap', custom_map=colour_override)
        
        image_output = Image.fromarray(colour_range.convert_to_rgb(heatmap))
        image_output = image_output.resize(output_resolution, Image.LANCZOS)

        if file_path is None:
            file_path = self.name.generate('Clicks', reload=True)
            
        if self.save:
            save_image_to_folder(image_output, file_path)
        
    def keyboard(self, last_session=False, file_path=None, colour_override=None):
        """Render keyboard image."""
        kb = DrawKeyboard(self.profile, self.data, last_session=last_session)
        
        image_output = kb.draw_image()

        if file_path is None:
            file_path = self.name.generate('Keyboard', reload=True)
            
        if self.save:
            save_image_to_folder(image_output, file_path)