import os
import sys
import shlex, subprocess
from pymediainfo import MediaInfo
from optparse import OptionParser


def getTrack(mediaInfo, track_type):

    for track in mediaInfo.tracks:
        if track.track_type == track_type:
            return track

    return None

def touch(vfile, dest_path):
    cmd = 'touch -r \"%s\" \"%s\"' % ( vfile, dest_path )
    print('')
    print(cmd)
    print('')
    os.system(cmd)


def main():
    # usage description
    usage = "Usage: python %prog [options] \nExample: python %prog -l video_files_rotation.txt"

    # input parameters
    parser = OptionParser(usage=usage)

    parser.add_option("-l", "--list", dest="flist",
                      help="List of video files, rotation angles and conversion modes (This parameter is mandatory)",
                      metavar="LIST")

    parser.add_option("-n", "--dry_run", dest="dry_run", action="store_true",
                        help="Dry run",
                        default=False)

    (options, args) = parser.parse_args()

    # make sure all necessary input parameters are provided
    if not options.flist:
        print('Mandatory parameters missing')
        print('')
        parser.print_help()
        sys.exit(1)

    # define audio encoder
    audio_enc = 'aac'
    cmd = 'ffmpeg -encoders'
    p = subprocess.Popen(shlex.split(cmd), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = p.communicate()
    if b'libfdk_aac' in out:
        audio_enc = 'libfdk_aac'
    #print(audio_enc)

    lines = open(options.flist).read().splitlines()

    pruned_lines = []
    # skip commented out or empty lines
    for line in lines:
        if line.strip().startswith('#') or line.strip() == '':
            continue
        pruned_lines.append( line )

    for counter, line in enumerate(pruned_lines, 1):
        split_line = line.strip().split(':')
        vfile, angle, mode = [split_line[i].strip() for i in (0, 1, 2)]
        #print(vfile, angle, mode)

        filename = os.path.basename(vfile)
        dest_folder = os.path.join(os.path.dirname(vfile), 'rotated')
        #print(dest_folder)

        if not os.path.exists(dest_folder) and not options.dry_run:
            os.system('mkdir -p \"%s\"' % dest_folder)

        dest_path = os.path.join(dest_folder, filename)

        print('===============================================')
        os.system('echo `date`')
        print('Processing file', counter)
        print(vfile)
        print('')

        cmd = 'mediainfo -f --Output=OLDXML \"%s\"' % vfile
        p = subprocess.Popen(shlex.split(cmd), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        xml_mediaInfo, err = p.communicate()

        mediaInfo = MediaInfo(xml_mediaInfo.decode())

        general = getTrack(mediaInfo, 'General')

        if mode == 'repack':
            # preserve old comment if already transcoded or add a comment if repacking is done for the first time
            comment = ( general.comment if general.comment else 'ffmpeg: video and audio repack' )

            cmd = 'ffmpeg -i \"%s\" -c copy -map_metadata 0 -metadata:s:v:0 rotate="%s" -metadata comment="%s" -y \"%s\"' % (vfile, angle, comment, dest_path)
            print(cmd)
            print('')
            if not options.dry_run:
                r = os.system(cmd)
                if r:
                    print('ffmpeg repacking failed! Skipping...')
                    continue
        elif mode == 'transcode':
            video   = getTrack(mediaInfo, 'Video')

            comment  = general.comment
            video_br = video.bit_rate

            rotation_lut = {
                "-90" : "transpose=1",
                "90"  : "transpose=2",
                "180" : "transpose=2,transpose=2"
            }
            video_filt = '-vf "' + rotation_lut[angle] + '" '

            print('Input file comment:', comment)
            print('')
            if 'video and audio repack' not in comment and 'video repack' not in comment:
                print('File does not contain a repacked video stream! Need to start from the original file with the following video filter:')
                print(' ', video_filt)
                print('Skipping...')
                continue

            # updated comment
            new_comment = 'ffmpeg: video and audio transcode'
            if 'audio repack' in comment:
                new_comment = 'ffmpeg: video transcode, audio repack'

            # video encoding options
            video_options_1st_pass = '%s-c:v libx265 -b:v %s -x265-params pass=1' % (video_filt, video_br)
            video_options = '%s-c:v libx265 -b:v %s -x265-params pass=2' % (video_filt, video_br)

            fmt = 'mp4'
            if vfile.lower().endswith('.mkv'):
                fmt = 'matroska'

            cmd = 'ffmpeg -i \"%s\" %s -an -f %s -y /dev/null' % (vfile, video_options_1st_pass, fmt)
            print(cmd)
            print('')
            if not options.dry_run:
                r = os.system(cmd)
                if r:
                    print('ffmpeg 1st pass failed! Skipping...')
                    continue

            cmd = 'ffmpeg -i \"%s\" %s -c:a copy -map_metadata 0 -metadata comment="%s" -y \"%s\"' % (vfile, video_options, new_comment, dest_path)
            print('')
            print(cmd)
            print('')
            if not options.dry_run:
                r = os.system(cmd)
                if r:
                    print('ffmpeg 2nd pass failed! Skipping...')
                    continue
        else:
            mode = None
            print('Unknown conversion mode. Nothing to do')

        if not options.dry_run and mode:
            touch(vfile, dest_path)

    print('===============================================')
    os.system('echo `date`')
    print('')



if __name__ == '__main__':
    main()

