import os
import shutil
import sys


def moveTree(sourceRoot, destRoot):
    try:
        os.makedirs(destRoot)
    except OSError:
        pass
    if not os.path.exists(destRoot):
        return False
    ok = True
    for path, dirs, files in os.walk(sourceRoot):
        relPath = os.path.relpath(path, sourceRoot)
        destPath = os.path.join(destRoot, relPath)
        if not os.path.exists(destPath):
            os.makedirs(destPath)
        for file in files:
            destFile = os.path.join(destPath, file)
            if os.path.isfile(destFile):
                print 'Skipping existing file: ' + os.path.join(relPath, file)
                ok = False
                continue
            print 'Moving file: ' + os.path.join(relPath, file)
            srcFile = os.path.join(path, file)
            os.rename(srcFile, destFile)
    for path, dirs, files in os.walk(sourceRoot, False):
        if len(files) == 0 and len(dirs) == 0:
            os.rmdir(path)
    return ok

    
def move_all(final_folder, *args):
    try:
        for folder in args:
            moveTree(folder, final_folder)
            shutil.rmtree(folder)
            new_name = folder.replace('\\', '/').split('/')[-1]
            shutil.rmtree('Build/{}'.format(new_name))
            os.remove('{}.spec'.format(new_name))
    except WindowsError:
        try:
            os.rmdir(final_folder)
        except OSError:
            pass
        return False
    return True

    
if __name__ == '__main__':
    del sys.argv[0]
    dest_folder = sys.argv.pop(0)
    try:
        shutil.rmtree(dest_folder)
    except WindowsError:
        pass
    if move_all(dest_folder, *sys.argv):
        print 'Finished moving files.'
    else:
        print 'Failed to move files.'
    try:
        shutil.rmtree('dist')
    except WindowsError:
        pass
