import os
import sys

project_root = os.environ.get('GITHUB_WORKSPACE', '.')
if project_root not in sys.path:
   sys.path.append(project_root)

from mousetracks2 import __version__ as version

tag_name = f'v{version}'
release_name = f'MouseTracks {version}'

print(f'Extracted Version: {version}')
print(f'Generated Tag Name: {tag_name}')
print(f'Generated Release Name: {release_name}')

# Write to GITHUB_OUTPUT for step outputs
if 'GITHUB_OUTPUT' in os.environ:
    with open(os.environ['GITHUB_OUTPUT'], 'a') as fh_output:
        print(f'version={version}', file=fh_output)
        print(f'tag_name={tag_name}', file=fh_output)
        print(f'release_name={release_name}', file=fh_output)

# Write to GITHUB_ENV for environment variables
if 'GITHUB_ENV' in os.environ:
    with open(os.environ['GITHUB_ENV'], 'a') as fh_env:
        print(f'VERSION={version}', file=fh_env)
