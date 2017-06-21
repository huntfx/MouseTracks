from __future__ import division
from operator import itemgetter
from core.files import load_program
from core.messages import date_format
from core.functions import ticks_to_seconds

print('Type profile name to load:')
program = raw_input()
data = load_program(program, _update_version=False)

print('Version: {}'.format(data['Version']))
print('Number of times loaded: {}'.format(data['TimesLoaded']))

time_elapsed_total = data['Ticks']['Total']
time_elapsed_session = time_elapsed_total - data['Ticks']['Session']['Total']
print('Time elapsed (total):  {}'.format(ticks_to_seconds(time_elapsed_total, 60)))
print('Time elapsed (last session):  {}'.format(ticks_to_seconds(time_elapsed_session, 60)))
print('Time recorded: {}'.format(ticks_to_seconds(data['Ticks']['Recorded'], 60)))

print('Created: {}'.format(date_format(data['Time']['Created'])))
print('Last saved: {}'.format(date_format(data['Time']['Modified'])))

num_keys = len(data['Keys']['Held'])
max_keys = 20
if num_keys > 1:
    print('Top {} key presses:'.format(min(num_keys, max_keys)))
elif num_keys == 1:
    print('Key press:')
for key, time_pressed in sorted(data['Keys']['Held'].items(), key=itemgetter(1))[:-max_keys - 1:-1]:
    num_presses = data['Keys']['Pressed'][key]
    print('  {k}: {t} ({n} press{s})'.format(k=key,
                                             t=ticks_to_seconds(time_pressed, 60),
                                             n=num_presses,
                                             s='' if num_presses == 1 else 'es'))
    
num_clicks = [0, 0, 0]
click_resolutions = set()
for resolution, button_clicks in data['Maps']['Clicks'].iteritems():
    click_resolutions.add(resolution)
    for i, button in enumerate(button_clicks):
        for pixel, clicks in button.iteritems():
            num_clicks[i] += clicks
print('Total clicks: {}'.format(sum(num_clicks)))
print('  LMB clicks: {}'.format(num_clicks[0]))
print('  MMB clicks: {}'.format(num_clicks[1]))
print('  RMB clicks: {}'.format(num_clicks[2]))

print 'Track Resolutions: {}'.format((data['Maps']['Tracks'].keys()))
print 'Click Resolutions: {}'.format(list(click_resolutions))

raw_input('Press enter to exit.')
