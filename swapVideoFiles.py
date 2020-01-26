import os
import sys
from optparse import OptionParser


# usage description
usage = "Usage: python %prog [options] \nExample: python %prog -s /home/ferencek/Pictures/ -d test_transcode"

# input parameters
parser = OptionParser(usage=usage)

parser.add_option("-n", "--dry_run", dest="dry_run", action="store_true",
                    help="Dry run",
                    default=False)

(options, args) = parser.parse_args()


original_source      = '/media/ferencek/Backup/backup/Pictures/'
original_destination = '/media/ferencek/Backup/transcoding/Pictures/original/'

transcoded_source = '/media/ferencek/Backup/transcoding/Pictures/transcoded/'


lines = file('video_files_processed_updated.txt').readlines()

pruned_lines = []

# skip commented out or empty lines
for line in lines:
    if line.strip().startswith('#') or line.strip() == '':
        continue
    pruned_lines.append( line )

for counter, line in enumerate(pruned_lines, 1):
    split_line = line.strip().split(' : ')

    original_file = split_line[0].strip().replace('/media/ferencek/ext_drive/backup/Pictures/', '/media/ferencek/Backup/backup/Pictures/')

    transcoded_file = split_line[1].strip().replace('/hdd-data/ferencek/Videos/Workshop/Pictures/', '/media/ferencek/Backup/transcoding/Pictures/')

    #print original_file, transcoded_file

    print '==============================================='
    print 'Processing file', counter
    print original_file
    print ''

    # check that the files exist before attempting to move/copy them
    if not os.path.exists(original_file):
        print 'Original file', original_file, 'missing'
        sys.exit(1)
    if not os.path.exists(transcoded_file):
        print 'New file', transcoded_file, 'missing'
        sys.exit(1)

    # check if the new directory for original files exists and create it if necessary
    dest_folder_original = os.path.join( original_destination, os.path.dirname(original_file)[len(original_source):] )
    #print dest_folder_original

    if not os.path.exists(dest_folder_original):
        if not options.dry_run:
            os.system('mkdir -p \"%s\"' % dest_folder_original)

    filename_original = os.path.basename(original_file)

    dest_path_original = os.path.join(dest_folder_original, filename_original)


    dest_folder_transcoded = os.path.join( original_source, os.path.dirname(transcoded_file)[len(transcoded_source):] )
    #print dest_folder_transcoded

    if not os.path.exists(dest_folder_transcoded):
        print 'Destination file for the transcoded file not found. This is not expected. Aborting'
        sys.exit(2)

    filename_transcoded = os.path.basename(transcoded_file)

    dest_path_transcoded = os.path.join(dest_folder_transcoded, filename_transcoded)


    cmd = 'mv -v \"%s\" \"%s\"' % (original_file, dest_path_original)
    print cmd
    if not options.dry_run:
        os.system(cmd)
    print ''

    cmd = 'mv -v \"%s\" \"%s\"' % (transcoded_file, dest_path_transcoded)
    print cmd
    if not options.dry_run:
        os.system(cmd)
    print ''

print '==============================================='
