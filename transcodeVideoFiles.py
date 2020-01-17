import os
import sys
import pickle
import tempfile
import json
import datetime
import shlex, subprocess
from optparse import OptionParser

# character encoding hack
reload(sys)
sys.setdefaultencoding('utf8')


def findStreams(f, data):

    video_idx = -1
    audio_idx = -1

    try:
        for index, info in enumerate(data['streams']):
            if video_idx >= 0 and audio_idx >= 0:
                break
            try:
                if info['codec_type'] == 'video' and video_idx < 0:
                    video_idx = index
                if info['codec_type'] == 'audio' and audio_idx < 0:
                    audio_idx = index
            except KeyError:
                print ''
                print 'Problem with finding codec_type info for', f
                print data
                print ''
    except KeyError:
        print ''
        print 'Problem with finding streams info for', f
        print data
        print ''

    return video_idx, audio_idx

def collectFiles(path, extensions, files):

    for entry in os.listdir(path):
        fullpath = os.path.join(path,entry)

        if entry.startswith('.'): continue

        if os.path.isdir(fullpath):
            collectFiles(fullpath, extensions, files)
        else:
            if not entry.lower().endswith(extensions): continue
            files.append(fullpath)

def selectFiles(video_files, source, files, checkBitRate=False, v_br=0.0, a_br=0.0):

    tmp = tempfile.NamedTemporaryFile(delete=False)
    #print tmp.name

    total_duration = 0.

    for f in video_files:
        if not f.startswith(source): continue

        cmd = 'ffprobe -v quiet -print_format json -show_format -show_streams \"%s\" > %s' % (f, tmp.name)
        #print cmd
        os.system(cmd)

        data = {}

        try:
            data = json.load(open(tmp.name))
        except ValueError:
            print ''
            print 'Problem with getting media info for', f
            print ''
            continue

        # leave already transcoded files untouched
        try:
            if 'tags' in data['format'].keys():
                if 'comment' in data['format']['tags'].keys():
                    if 'ffmpeg transcode/repack' in data['format']['tags']['comment']:
                        print 'File', f, 'already transcoded. Skipping...'
                        continue
        except KeyError:
            print ''
            print 'Problem with finding format info for', f, 'Skipping...'
            print data
            print ''
            continue

        video_idx, audio_idx = findStreams(f, data)
        if video_idx < 0:
            print ''
            print 'Problem with finding video stream for', f, 'Skipping...'
            print data
            print ''
            continue
        if audio_idx < 0:
            print ''
            print 'Problem with finding audio stream for', f, 'Skipping...'
            print data
            print ''
            continue

        video_br = 0.
        audio_br = 0.
        channels = 2.

        try:
            video_br = float( data['streams'][video_idx]['bit_rate'] )
        except KeyError:
            print ''
            print 'Problem with getting video bit rate info for', f, 'Skipping...'
            print data
            print ''
            continue

        try:
            audio_br = float( data['streams'][audio_idx]['bit_rate'] )
        except KeyError:
            print ''
            print 'Problem with getting audio bit rate info for', f, 'Skipping...'
            print data
            print ''
            continue

        try:
            channels = float( data['streams'][audio_idx]['channels'] )
        except KeyError:
            print ''
            print 'Problem with getting audio channels info for', f, 'Skipping...'
            print data
            print ''
            continue

        # leave .mp4 and .mkv files that already meet the bit rate requirements untouched
        extensions = ('.mp4', '.mkv')
        if checkBitRate and f.lower().endswith(extensions) and video_br < v_br and audio_br < (channels * a_br)/2.:
            print 'File', f, 'already meets the bit rate requirements. Skipping...'
            print '  Video bit rate:', video_br/1e6, 'Mbps'
            print '  Audio channels:', int(channels)
            print '  Audio bit rate:', audio_br/1e3, 'kbps'
            continue

        try:
            # detect UHD videos
            if data['streams'][video_idx]['width'] > 1920:
                print ''
                print 'File', f, 'has width greater than 1920 pixels:', data['streams'][video_idx]['width']
        except KeyError:
            print ''
            print 'Problem with getting video width info for', f
            print data
            print ''

        total_duration += float(data['streams'][video_idx]['duration'])
        files.append([f, os.path.getsize(f), data, video_idx, audio_idx])

    tmp.close()
    os.unlink(tmp.name)
    return total_duration


def main():
    # usage description
    usage = "Usage: python %prog [options] \nExample: python %prog -s /home/ferencek/Pictures/ -d test_transcode"

    # input parameters
    parser = OptionParser(usage=usage)

    parser.add_option("-s", "--source", dest="source",
                      help="Source folder (This parameter is mandatory)",
                      metavar="SOURCE")

    parser.add_option("-d", "--destination", dest="destination",
                      help="Destination folder (This parameter is mandatory)",
                      metavar="DESTINATION")

    parser.add_option("-t", "--transcode", dest="transcode", action='store_true',
                      help="Transcode selected files",
                      default=False)

    parser.add_option("-r", "--rescan", dest="rescan", action='store_true',
                      help="Force rescan of the source folder",
                      default=False)

    parser.add_option("-n", "--dry_run", dest="dry_run", action="store_true",
                        help="Perform a transcoding dry run",
                        default=False)

    parser.add_option("-y", "--yadif", dest="yadif", action='store_true',
                      help="Enable deinterlacing",
                      default=False)

    (options, args) = parser.parse_args()

    # make sure all necessary input parameters are provided
    if not (options.source and options.destination):
        print 'Mandatory parameters missing'
        print ''
        parser.print_help()
        sys.exit(1)

    # define audio encoder
    audio_enc = 'aac'
    cmd = 'ffmpeg -encoders'
    p = subprocess.Popen(shlex.split(cmd), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = p.communicate()
    if 'libfdk_aac' in out:
        audio_enc = 'libfdk_aac'
    #print audio_enc

    source = options.source
    # make sure the source path is defined as an absolute path
    if not source.startswith('/'):
        source = os.path.join( os.path.abspath('.'), source )
    # make sure the source path end with '/'
    source = source.rstrip('/') + '/'

    # bit rate thresholds (in bps)
    # video bit rate
    v_br = 4.1e6
    # audio bit rate
    a_br = 140e3

    extensions = ('.mp4', '.m4v', '.mov', '.3gp', '.3g2', '.mpg', '.mpeg', '.mj2', '.wmv', '.avi', '.webm', '.mkv')
    #extensions += ('.ts', '.mts')

    video_files = []
    selected_files = []
    selected_files_list = []
    total_duration = 0.
    shouldRebuild = options.rescan

    if os.path.exists('video_files_all.pkl') and not shouldRebuild:
        with open('video_files_all.pkl', 'rb') as fpkl:
            (path, video_files) = pickle.load(fpkl)
            if not path.rstrip('/') in source:
                print 'Source folder', source, 'different from the cached folder', path
                print 'Source folder will be rescanned...'
                print ''
                shouldRebuild = True
                del video_files [:]
            else:
                print 'Pickled list of all video files loaded'

    if not os.path.exists('video_files_all.pkl') or shouldRebuild:
        print 'Building pickled list of all video files...'
        with open('video_files_all.pkl', 'wb') as fpkl:
            collectFiles(source, extensions, video_files)
            dump = (source, video_files)
            pickle.dump(dump, fpkl)
        print 'Pickled list of all video files built'
        file_list_all = open('video_files_all.txt','w')
        for v in video_files:
            file_list_all.write(v+'\n')
        file_list_all.close()

    print '\nFound', len(video_files), 'video files in', source, '\n'

    if os.path.exists('video_files_selected.pkl') and not shouldRebuild:
        with open('video_files_selected.pkl', 'rb') as fpkl:
            (path, total_duration, selected_files) = pickle.load(fpkl)
            if not path.rstrip('/') in source:
                shouldRebuild = True
                del selected_files [:]
                del selected_files_list [:]
            else:
                print 'Pickled list of selected video files loaded'

    if os.path.exists('video_files_selected.txt') and not shouldRebuild:
        with open('video_files_selected.txt', 'rb') as ftxt:
            selected_files_list = ftxt.read().splitlines()
            #print selected_files_list

    if not os.path.exists('video_files_selected.pkl') or shouldRebuild:
        print 'Building pickled list of selected video files...'
        with open('video_files_selected.pkl', 'wb') as fpkl:
            total_duration = selectFiles(video_files, source, selected_files, checkBitRate=True, v_br=v_br, a_br=a_br)
            dump = (source, total_duration, selected_files)
            pickle.dump(dump, fpkl)
        print 'Pickled list of selected video files built'
        for v in selected_files:
            selected_files_list.append(v[0])
        file_list_selected = open('video_files_selected.txt','w')
        file_list_skipped = open('video_files_skipped.txt','w')
        for v in video_files:
            if v in selected_files_list:
                file_list_selected.write(v+'\n')
            else:
                file_list_skipped.write(v+'\n')
        file_list_selected.close()
        file_list_skipped.close()

    print '\nSelected', len(selected_files), 'video files in', source, 'with a total duration of', str(datetime.timedelta(seconds=total_duration)), '\n'


    if options.transcode:

        source_prefix = source
        destination = options.destination

        totalSizeBefore = 0
        totalSizeAfter = 0

        file_list_processed = open('video_files_processed.txt','w')

        for counter, f in enumerate(selected_files, 1):

            if not f[0] in selected_files_list: continue

            filename = os.path.basename(f[0])

            bv = '4M'
            ba = '128k'

            video_br = float( f[2]['streams'][f[3]]['bit_rate'] )
            audio_br = float( f[2]['streams'][f[4]]['bit_rate'] )
            channels = float( f[2]['streams'][f[4]]['channels'] )
            total_br = 0.

            try:
                total_br = float( f[2]['format']['bit_rate'] )
            except KeyError:
                print ''
                print 'Problem with getting the total bit rate info for', f, 'Skipping...'
                print f[2]
                print ''
                continue

            # if mono, reduce the audio bit rate
            if int( channels ) == 1:
                ba = '64k'

            # make sure the destination path is defined as an absolute path
            if not destination.startswith('/'):
                destination = os.path.join( os.path.abspath('.'), destination )

            dest_folder = os.path.join( destination, os.path.dirname(f[0])[len(source_prefix):] )
            #print dest_folder

            if not os.path.exists(dest_folder) and not options.dry_run:
                os.system('mkdir -p \"%s\"' % dest_folder)

            print '==============================================='
            os.system('echo `date`')
            print 'Transcoding file', counter
            print f[0]
            print ''

            # check for corrupt video bit rate
            corrupt_video_br = False
            if video_br > 1.1 * total_br and video_br > 50e6:
                corrupt_video_br = True
                print 'File has a corrupt video bit rate info. Video stream will be transcoded with video bit rate set to (total - audio)'
                print '  Total bit rate:', total_br/1e6, 'Mbps'
                print '  Video bit rate:', video_br/1e6, 'Mbps'
                print '  Audio bit rate:', audio_br/1e3, 'kbps'
                video_br = total_br - audio_br
                print '  Fixed video bit rate:', video_br/1e6, 'Mbps'

            # figure out transcoding and repacking status
            copy_video = False
            if video_br < v_br:
                if not corrupt_video_br:
                    print 'File already meets the video bit rate requirements. Video stream will be repacked...'
                    print '  Video bit rate:', video_br/1e6, 'Mbps'
                    copy_video = True
                else:
                    bv = ( '%.0f' %  video_br )

            copy_audio = False
            if audio_br < (channels * a_br)/2.:
                print 'File already meets the audio bit rate requirements. Audio stream will be repacked...'
                print '  Audio channels:', int(channels)
                print '  Audio bit rate:', audio_br/1e3, 'kbps'
                copy_audio = True

            # video encoding options
            video_filt = ''
            if options.yadif:
                video_filt = '-vf yadif=mode=1:parity=-1:deint=0 '
            video_options_1st_pass = '%s-c:v libx265 -b:v %s -x265-params pass=1' % (video_filt, bv)
            video_options = '%s-c:v libx265 -b:v %s -x265-params pass=2' % (video_filt, bv)
            if copy_video:
                video_options = '-c:v copy'

            # audio encoding options
            audio_options = '-c:a %s -b:a %s' % (audio_enc, ba)
            if copy_audio:
                audio_options = '-c:a copy'

            fmt = 'mp4'
            extensions = ('.mp4', '.m4v', '.mov', '.3gp', '.3g2')
            if ( not copy_video and not copy_audio ) or filename.lower().endswith(extensions):
                filename = os.path.splitext(filename)[0] + '.mp4'
            else:
                filename = os.path.splitext(filename)[0] + '.mkv'
                fmt = 'mkv'

            dest_path = os.path.join(dest_folder, filename)

            if not copy_video:
                cmd = 'ffmpeg -i \"%s\" %s -an -f %s -y /dev/null' % (f[0], video_options_1st_pass, fmt)
                print cmd
                print ''
                if not options.dry_run:
                    r = os.system(cmd)
                    if r:
                        print 'ffmpeg failed! Skipping...'
                        continue

            cmd = 'ffmpeg -i \"%s\" %s %s -map_metadata 0 -metadata comment="ffmpeg transcode/repack" -y \"%s\"' % (f[0], video_options, audio_options, dest_path)
            print ''
            print cmd
            print ''
            if not options.dry_run:
                r = os.system(cmd)
                if r:
                    print 'ffmpeg failed! Attempting recovery...'
                    cmd = cmd.replace('ffmpeg ', 'ffmpeg -fflags +genpts ')
                    print ''
                    print cmd
                    print ''
                    r = os.system(cmd)
                    if r:
                        print 'ffmpeg failed again! Skipping...'
                        continue

            if not options.dry_run:
                os.system('touch -r \"%s\" \"%s\"' % ( f[0], dest_path ) )

            file_list_processed.write(f[0] + ' : ' + dest_path + '\n')

            totalSizeBefore += f[1]
            if not options.dry_run:
                totalSizeAfter  += os.path.getsize( dest_path )

        file_list_processed.close()

        print '==============================================='
        print ''
        print '\nTotal size before transcoding:', float(totalSizeBefore)/(1024.0**3), 'GB'
        print 'Total size before transcoding:', float(totalSizeAfter)/(1024.0**3), 'GB\n'


if __name__ == '__main__':
    main()

