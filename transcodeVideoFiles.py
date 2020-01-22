import os
import sys
import pickle
import datetime
import shlex, subprocess
from pymediainfo import MediaInfo
from optparse import OptionParser

# character encoding hack
reload(sys)
sys.setdefaultencoding('utf8')


def getTrack(mediaInfo, track_type):

    for track in mediaInfo.tracks:
        if track.track_type == track_type:
            return track

    return None

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

    total_duration = 0.

    for f in video_files:
        if not f.startswith(source): continue

        cmd = 'mediainfo -f --Output=OLDXML \"%s\"' % f
        p = subprocess.Popen(shlex.split(cmd), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        xml_mediaInfo, err = p.communicate()

        mediaInfo = MediaInfo(xml_mediaInfo)

        general = getTrack(mediaInfo, 'General')

        total_br = 0.

        # leave already transcoded files untouched
        if general:
            #print [attr for attr in dir(general) if not attr.startswith('__')]
            if general.comment:
                if 'ffmpeg: ' in general.comment:
                    print 'File', f, 'already transcoded. Skipping...'
                    continue
            if general.overall_bit_rate:
                total_br = float( general.overall_bit_rate )
            else:
                print 'Missing total bit rate info for', f, 'Skipping...'
                os.system('mediainfo \"%s\"' % f)
                continue
        else:
            print 'Problem with getting general info for', f, 'Skipping...'
            os.system('mediainfo \"%s\"' % f)
            continue

        audio_br = 0.
        channels = 2.

        audio = getTrack(mediaInfo, 'Audio')

        if audio:
            #print [attr for attr in dir(audio) if not attr.startswith('__')]
            if audio.bit_rate:
                audio_br = float( audio.bit_rate )
            else:
                print 'Missing audio bit rate info for', f, 'Skipping...'
                os.system('mediainfo \"%s\"' % f)
                continue
            if audio.channel_s:
                channels = float( audio.channel_s )
            else:
                print 'Missing audio channels info for', f, 'Skipping...'
                os.system('mediainfo \"%s\"' % f)
                continue
        else:
            print 'Problem with finding audio stream for', f, 'Skipping...'
            os.system('mediainfo \"%s\"' % f)
            continue

        video_br = 0.

        video = getTrack(mediaInfo, 'Video')

        if video:
            #print [attr for attr in dir(video) if not attr.startswith('__')]
            if video.bit_rate:
                video_br = float( video.bit_rate )
            else:
                print 'Missing video bit rate info for', f
        else:
            print 'Problem with finding video stream for', f, 'Skipping...'
            os.system('mediainfo \"%s\"' % f)
            continue

        # leave .mp4 and .mkv files that already meet the bit rate requirements untouched
        extensions = ('.mp4', '.mkv')
        if checkBitRate and f.lower().endswith(extensions) and video.bit_rate and video_br < v_br and audio_br < (channels * a_br)/2.:
            print 'File', f, 'already meets the bit rate requirements. Skipping...'
            print '  Video bit rate:', video_br/1e6, 'Mbps'
            print '  Audio channels:', int(channels)
            print '  Audio bit rate:', audio_br/1e3, 'kbps'
            continue

        # detect UHD videos
        if video.width:
            if int( video.width ) > 1920:
                print 'File', f, 'has width greater than 1920 pixels:', video.width
        else:
            print 'Problem with getting video width info for', f
            os.system('mediainfo \"%s\"' % f)

        # duration stored in ms, converting to s
        if general.duration:
            total_duration += float( general.duration ) / 1e3
        else:
            print 'Problem with getting duration info for', f, 'Skipping...'
            os.system('mediainfo \"%s\"' % f)
            continue
        files.append([f, os.path.getsize(f), xml_mediaInfo])

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

    parser.add_option("--deint", dest="deint", action='store_true',
                      help="Enable deinterlacing",
                      default=False)
    
    parser.add_option("--size", dest="size", action='store_true',
                      help="Check transcoded file size",
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
    extensions_ts = ('.ts', '.mts')
    #extensions += extensions_ts

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
        file_list_failed = open('video_files_failed.txt','w')

        for counter, f in enumerate(selected_files, 1):

            if not f[0] in selected_files_list: continue

            filename = os.path.basename(f[0])

            bv = '4M'
            ba = '128k'

            mediaInfo = MediaInfo(f[2])
            general   = getTrack(mediaInfo, 'General')
            audio     = getTrack(mediaInfo, 'Audio')
            video     = getTrack(mediaInfo, 'Video')

            total_br = float( general.overall_bit_rate )
            audio_br = float( audio.bit_rate )
            channels = float( audio.channel_s )

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
            print 'Processing file', counter
            print f[0]
            print ''

            video_br = 0.

            # check video bit rate info
            if video.bit_rate:
                video_br = float( video.bit_rate )
            else:
                print 'Missing video bit rate info, setting it to (total - audio)'
                print '  Total bit rate:', total_br/1e6, 'Mbps'
                print '  Video bit rate: N/A'
                print '  Audio bit rate:', audio_br/1e3, 'kbps'
                print '  Audio channels:', int(channels)
                video_br = total_br - audio_br
                print '  Fixed video bit rate:', video_br/1e6, 'Mbps'

            # check for corrupt total bit rate
            corrupt_total_br = False
            if video_br > 1.1 * total_br:
                corrupt_total_br = True
                print 'Total bit rate info is potentially corrupt. Assuming video and audio bit rates to be correct...'
                print '  Total bit rate:', total_br/1e6, 'Mbps'
                print '  Video bit rate:', video_br/1e6, 'Mbps'
                print '  Audio bit rate:', audio_br/1e3, 'kbps'
                print '  Audio channels:', int(channels)

            # figure out transcoding and repacking status
            copy_video = False
            if video_br < v_br:
                print 'File already meets the video bit rate and codec requirements. Video stream will be repacked...'
                print '  Video bit rate:', video_br/1e6, 'Mbps'
                copy_video = True

            unsupported_audio_codecs = ['raw', 'samr']
            audio_codec = ''
            if audio.codec_id:
                audio_codec = audio.codec_id.strip()
            elif audio.id:
                audio_codec = audio.id.strip()
            copy_audio = False
            if audio_br < (channels * a_br)/2. and audio_codec not in unsupported_audio_codecs:
                print 'File already meets the audio bit rate and codec requirements. Audio stream will be repacked...'
                print '  Audio channels:', int(channels)
                print '  Audio bit rate:', audio_br/1e3, 'kbps'
                copy_audio = True

            # comment
            comment = 'ffmpeg: video and audio transcode'
            if copy_video and copy_audio:
                comment = 'ffmpeg: video and audio repack'
            elif (copy_video and not copy_audio) or (not copy_video and copy_audio):
                comment = 'ffmpeg: video ' + ('repack' if copy_video else 'transcode') + ', audio ' + ('repack' if copy_audio else 'transcode')

            # video encoding options
            video_filt = ''
            if options.deint:
                video_filt = '-vf "yadif=0:-1:0" '
            # workaround for AVI files (by default pix_fmt=yuvj422p is used which results in strange artifacts in a x265-encoded video stream)
            pix_fmt = ''
            if filename.lower().endswith('.avi'):
                pix_fmt = ' -pix_fmt yuv422p'
            video_options_1st_pass = '%s-c:v libx265 -b:v %s -x265-params pass=1%s' % (video_filt, bv, pix_fmt)
            video_options = '%s-c:v libx265 -b:v %s -x265-params pass=2%s' % (video_filt, bv, pix_fmt)
            if copy_video:
                video_options = '-c:v copy'

            # audio encoding options
            audio_options = '-c:a %s -b:a %s' % (audio_enc, ba)
            if copy_audio:
                audio_options = '-c:a copy'

            fmt = 'mp4'
            extensions = ('.mp4', '.m4v', '.mov', '.3gp', '.3g2')
            if ( not copy_video and not copy_audio and not filename.lower().endswith(extensions_ts) ) or filename.lower().endswith(extensions):
                filename = os.path.splitext(filename)[0] + '.mp4'
            else:
                filename = os.path.splitext(filename)[0] + '.mkv'
                fmt = 'matroska'

            dest_path = os.path.join(dest_folder, filename)

            if not copy_video:
                cmd = 'ffmpeg -i \"%s\" %s -an -f %s -y /dev/null' % (f[0], video_options_1st_pass, fmt)
                print cmd
                print ''
                if not options.dry_run:
                    r = os.system(cmd)
                    if r:
                        print 'ffmpeg 1st pass failed! Skipping...'
                        file_list_failed.write(f[0] + '\n')
                        continue

            cmd = 'ffmpeg -i \"%s\" %s %s -map_metadata 0 -metadata comment="%s" -y \"%s\"' % (f[0], video_options, audio_options, comment, dest_path)
            print ''
            print cmd
            print ''
            if not options.dry_run:
                r = os.system(cmd)
                if r:
                    if f[0].lower().endswith('.mpg'):
                        print 'ffmpeg failed! Attempting recovery...'
                        cmd = cmd.replace('ffmpeg -i', 'ffmpeg -fflags +genpts -i')
                        print ''
                        print cmd
                        print ''
                        r = os.system(cmd)
                        if r:
                            print 'ffmpeg failed again! Skipping...'
                            file_list_failed.write(f[0] + '\n')
                            continue
                    else:
                        if not copy_video:
                            print 'ffmpeg 2nd pass failed! Skipping...'
                        else:
                            print 'ffmpeg failed! Skipping...'
                        file_list_failed.write(f[0] + '\n')
                        continue

            if not options.dry_run:
                cmd = 'touch -r \"%s\" \"%s\"' % ( f[0], dest_path )
                print ''
                print cmd
                print ''
                os.system(cmd)

            file_list_processed.write(f[0] + ' : ' + dest_path + '\n')

            totalSizeBefore += f[1]
            if not options.dry_run or options.size:
                totalSizeAfter  += os.path.getsize( dest_path )

        file_list_processed.close()
        file_list_failed.close()

        print '==============================================='
        os.system('echo `date`')
        print ''
        print '\nTotal size before transcoding:', float(totalSizeBefore)/(1024.0**3), 'GB'
        print 'Total size before transcoding:', float(totalSizeAfter)/(1024.0**3), 'GB\n'


if __name__ == '__main__':
    main()

