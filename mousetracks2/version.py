"""Set the current application version.
This is used for both the application and build process.

Updating this file will trigger a release using the version number.
The process is as follows:
1. Commit `version.py`.
2. Create git tag named `v{VERSION}` (eg. v2.0.0).
3. Create release, using the commit message as release notes.
4. Build executable and attach to release.

Some processing will be done on the commit message so the format can be
kept simple. The recommend commit message format is as follows:
    Created new option.
    # Enhancements
    - New option
    # Fixes
    - Fixed potential crash when thing happens ({commit_sha})
"""

VERSION = '2.2.7'
