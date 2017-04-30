from __future__ import division
import numpy as np

from core.constants import CONFIG
from core.files import load_program
from core.image import *
from core.image_heatmap import generate as generate_heatmap
from core.image_tracks import generate as generate_tracks

#Options
profile = 'default'
desired_resolution = (CONFIG.data['GenerateImages']['OutputResolutionX'],
                      CONFIG.data['GenerateImages']['OutputResolutionY'])

print 'Loading profile: {}'.format(profile)
main_data = load_program(profile)
print 'Desired resolution: {}x{}'.format(*desired_resolution)

generate_tracks('Result/Recent Tracks.png', main_data['Tracks'])    
generate_heatmap('Result/Recent Clicks.png', main_data['Clicks'])
