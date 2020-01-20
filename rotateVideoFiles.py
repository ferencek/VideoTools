import os
import sys
from optparse import OptionParser

# character encoding hack
reload(sys)
sys.setdefaultencoding('utf8')


def main():
    # usage description
    usage = "Usage: python %prog [options] \nExample: python %prog -l video_files_rotation.txt"

    # input parameters
    parser = OptionParser(usage=usage)

    parser.add_option("-l", "--list", dest="flist",
                      help="List of video files and rotation angles (This parameter is mandatory)",
                      metavar="LIST")

    parser.add_option("-n", "--dry_run", dest="dry_run", action="store_true",
                        help="Dry run",
                        default=False)

    (options, args) = parser.parse_args()

    # make sure all necessary input parameters are provided
    if not options.flist:
        print 'Mandatory parameters missing'
        print ''
        parser.print_help()
        sys.exit(1)

    lines = file(options.flist).readlines()
    for line in lines:
        # skip commented out or empty lines
        if line.strip().startswith('#') or line.strip() == '':
            continue
        sline = line.strip().split(':')
        vfile = sline[0].strip()
        angle = sline[1].strip()
        #print vfile, angle

        dest_folder = os.path.dirname(vfile).replace('/transcoded/', '/rotated/')
        #print dest_folder

        if not os.path.exists(dest_folder) and not options.dry_run:
            os.system('mkdir -p \"%s\"' % dest_folder)

        dest_path = vfile.replace('/transcoded/', '/rotated/')

        cmd = 'ffmpeg -i \"%s\" -c copy -map_metadata 0 -metadata:s:v:0 rotate="%s" -y \"%s\"' % (vfile, angle, dest_path)
        print ''
        print cmd
        print ''
        if not options.dry_run:
            os.system(cmd)

            cmd = 'touch -r \"%s\" \"%s\"' % ( vfile, dest_path )
            print ''
            print cmd
            print ''
            os.system(cmd)


if __name__ == '__main__':
    main()

