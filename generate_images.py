from __future__ import division


def simple_bit_mask(selection, size, default_all=True):
    """Turn a range of numbers into True and False.
    For example, [1, 3, 4] would result in [True, False, True, True].
    I'm aware it's probably a bit overkill, kinda liked the idea though.
    """
    
    #Calculate total
    total = 0
    for n in selection:
        try:
            total += pow(2, int(n) - 1)
        except ValueError:
            pass
    
    #Convert to True or False
    values = map(bool, list(map(int, str(bin(total))[2:]))[::-1])
    size_difference = max(0, size - len(values))
    if size_difference:
        values += [False] * size_difference
    
    #Set to use everything if an empty selection is given
    if default_all:
        if not any(values):
            values = [True] * size
    
    return values


def round_up(n):
    i = int(n)
    if float(n) - i:
        i += 1
    return i


print('Type profile to load, or type "list" to see them all:')
profile = raw_input()

if profile == 'list':
    
    from core.files import list_files, format_name
    from core.functions import RunningPrograms

    #Read the data folder and format names
    all_files = sorted(list_files())
    programs = {}
    for program_name in RunningPrograms(list_only=True).programs.values():
        programs[format_name(program_name)] = program_name
    all_files = [f for f in all_files if f in programs]

    page = 1
    limit = 6
    maximum = len(all_files)
    total_pages = round_up(maximum / limit)

    #Ask for user input
    while True:
        offset = (page - 1) * limit

        results = all_files[offset:offset + limit]
        for i, r in enumerate(results):
            print('{}: {}'.format(i + offset + 1, programs[r]))
        print('Page {} of {}. Type "page <number>" to switch.'.format(page, total_pages))
        print('You can type the number or name of a profile to load it.')

        profile = raw_input()
        last_page = page
        if profile.startswith('page '):
            try:
                page = int(profile.split()[1])
                if not 0 < page <= total_pages:
                    page = last_page
                    raise ValueError
            except (ValueError, IndexError):
                print('Invalid page number')
        elif profile == '>':
            if page < total_pages:
                page += 1
        elif profile == '<':
            if page > 1:
                page -= 1
        else:
            try:
                num = int(profile) - 1
                if not 0 < num <= maximum:
                    raise IndexError
                profile = programs[all_files[num]]
                break
            except ValueError:
                break
            except IndexError:
                print('Number doesn\'t match any profiles')


generate_tracks = False
generate_heatmap = False

print('What do you want to generate?')
print('Separate options with a space, or hit enter for all.')
print('1: Tracks')
print('2: Click Heatmap')

result = simple_bit_mask(raw_input().split(), 2)

if result[0]:
    generate_tracks = True
    
if result[1]:
    from core.constants import CONFIG
    
    generate_heatmap = True
    print('Which mouse buttons should be included in the heatmap?.')
    print('Separate options with a space, or hit enter for all.')
    print('1: Left Mouse Button')
    print('2: Middle Mouse Button')
    print('3: Right Mouse Button')
    heatmap_buttons = map(bool, simple_bit_mask(raw_input().split(), 3))
    CONFIG['GenerateHeatmap']['MouseButtonLeft'] = heatmap_buttons[0]
    CONFIG['GenerateHeatmap']['MouseButtonMiddle'] = heatmap_buttons[1]
    CONFIG['GenerateHeatmap']['MouseButtonRight'] = heatmap_buttons[2]
    if not heatmap_buttons:
        generate_heatmap = False

if generate_tracks or generate_heatmap:
    print('Importing modules...')
    from core.image import RenderImage

    print('Loading profile {}...'.format(profile))
    r = RenderImage(profile)

    if generate_tracks:
        r.generate('Tracks')
    if generate_heatmap:
        r.generate('Clicks')
else:
    print('Nothing was set to generate.')
