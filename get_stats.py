from __future__ import division
from operator import itemgetter
from core.files import load_program
from core.messages import date_format

_LENGTH = (
    ('second', 1, 60, 2),
    ('minute', 60, 60, None),
    ('hour', 60 * 60, 24, None),
    ('day', 60 * 60 * 24, 7, None),
    ('week', 60 * 60 * 24 * 7, 52, None),
    ('year', 60 * 60 * 24 * 365, None, None)
)

def ticks_to_seconds(amount, tick_rate, output_length=2):  

    output = []
    time_elapsed = amount / tick_rate
    for name, length, limit, decimals in _LENGTH[::-1]:
        if decimals is None:
            current = int(time_elapsed // length)
        else:
            current = round(time_elapsed / length, 2)
        if limit is not None:
            current %= limit

        if current:
            output.append('{} {}{}'.format(current, name, '' if current == 1 else 's'))
            if len(output) == output_length:
                break
            
    if len(output) > 1:
        result = ' and '.join((', '.join(output[:-1]), output[-1]))
    else:
        result = output[-1]

    return result


data = load_program('Default', _update_version=False)

print 'Version: {}'.format(data['Version'])
print 'Number of times loaded: {}'.format(data['TimesLoaded'])

print 'Time elapsed:  {}'.format(ticks_to_seconds(data['Ticks']['Total'], 60))
print 'Time recorded: {}'.format(ticks_to_seconds(data['Ticks']['Recorded'], 60))

print 'Created: {}'.format(date_format(data['Time']['Created']))
print 'Last saved: {}'.format(date_format(data['Time']['Modified']))

num_keys = len(data['Keys']['Held'])
max_keys = 20
if num_keys > 1:
    print 'Top {} key presses:'.format(min(num_keys, max_keys))
elif num_keys == 1:
    print 'Key press:'
for key, time_pressed in sorted(data['Keys']['Held'].items(), key=itemgetter(1))[:-max_keys - 1:-1]:
    num_presses = data['Keys']['Pressed'][key]
    print '  {k}: {t} ({n} press{s})'.format(k=key,
                                             t=ticks_to_seconds(time_pressed, 60),
                                             n=num_presses,
                                             s='' if num_presses == 1 else 'es')
    
num_clicks = [0, 0, 0]
for resolution, button_clicks in data['Maps']['Clicks'].iteritems():
    for i, button in enumerate(button_clicks):
        for pixel, clicks in button.iteritems():
            num_clicks[i] += clicks
print 'Total clicks: {}'.format(sum(num_clicks))
print '  LMB clicks: {}'.format(num_clicks[0])
print '  MMB clicks: {}'.format(num_clicks[1])
print '  RMB clicks: {}'.format(num_clicks[2])
