import os
import sys
from optparse import OptionParser


# usage description
usage = "Usage: python %prog [options]"

# input parameters
parser = OptionParser(usage=usage)

parser.add_option("-s", "--source", dest="source",
                  help="Source folder (This parameter is mandatory)",
                  metavar="SOURCE")

parser.add_option("-d", "--destination", dest="destination",
                  help="Destination folder (This parameter is mandatory)",
                  metavar="DESTINATION")

parser.add_option("-b", "--backup", dest="backup",
                  help="Backup folder for source files. The folder will be created if it does not already exist. (This parameter is mandatory)",
                  metavar="BACKUP")

parser.add_option("-n", "--dry_run", dest="dry_run", action="store_true",
                    help="Dry run",
                    default=False)

(options, args) = parser.parse_args()


source = options.source
# make sure the source path is defined as an absolute path
if not source.startswith('/'):
    source = os.path.join( os.path.abspath('.'), source )
# make sure the source path ends with '/'
source = source.rstrip('/') + '/'

destination = options.destination
# make sure the destination path is defined as an absolute path
if not destination.startswith('/'):
    destination = os.path.join( os.path.abspath('.'), destination )
# make sure the destination path ends with '/'
destination = destination.rstrip('/') + '/'

backup = options.backup
# make sure the backup path is defined as an absolute path
if not backup.startswith('/'):
    backup = os.path.join( os.path.abspath('.'), backup )
# make sure the backup path ends with '/'
backup = backup.rstrip('/') + '/'

lines = open('video_files_processed.txt').read().splitlines()

pruned_lines = []

# skip commented out or empty lines
for line in lines:
    if line.strip().startswith('#') or line.strip() == '':
        continue
    pruned_lines.append( line )

for counter, line in enumerate(pruned_lines, 1):
    split_line = line.strip().split(' : ')

    original_file = split_line[0].strip()

    transcoded_file = split_line[1].strip()

    #print(original_file, transcoded_file)

    print('===============================================')
    print('Processing file', counter)
    print(original_file)
    print('')

    # check that the files exist before attempting to move/copy them
    if not os.path.exists(original_file):
        print('Original file', original_file, 'missing')
        sys.exit(1)
    if not os.path.exists(transcoded_file):
        print('New file', transcoded_file, 'missing')
        sys.exit(1)

    # check if the new directory for original files exists and create it if necessary
    backup_folder = os.path.join( backup, os.path.dirname(original_file)[len(source):] )
    #print(backup_folder)

    if not os.path.exists(backup_folder):
        if not options.dry_run:
            os.system('mkdir -p \"%s\"' % backup_folder)

    original_folder = os.path.dirname(original_file)
    #print(original_folder)

    if not os.path.exists(original_folder):
        print('Destination folder for the transcoded file not found. This is not expected. Aborting')
        sys.exit(2)

    cmd = 'mv -v \"%s\" \"%s\"' % (original_file, backup_folder)
    print(cmd)
    if not options.dry_run:
        os.system(cmd)
    print('')

    cmd = 'mv -v \"%s\" \"%s\"' % (transcoded_file, original_folder)
    print(cmd)
    if not options.dry_run:
        os.system(cmd)
    print('')

print('===============================================')
