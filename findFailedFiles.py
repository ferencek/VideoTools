import sys
from optparse import OptionParser


def findFailedFiles(path):

    selected_files = []
    processed_files = []
    failed_files = []

    lines = file('video_files_selected_full.txt').readlines()
    for line in lines:
        selected_files.append(line.strip())

    lines = file('video_files_processed.txt').readlines()
    for line in lines:
        processed_files.append(line.split(' : ')[0].strip())

    #lines = file('video_files_failed.txt').readlines()
    #for line in lines:
        #failed_files.append(line.strip())

    #print(selected_files)
    #print('')
    #print(processed_files)
    #print('')
    #print(failed_files)

    for f in selected_files:
        #print(f)
        if f not in processed_files:
            print(f)
        #if f not in processed_files and f not in failed_files:
            #print(f)


def main():
    # usage description
    usage = "Usage: python %prog [options] \nExample: python %prog -p /path/to/files/"

    # input parameters
    parser = OptionParser(usage=usage)

    parser.add_option("-p", "--path", dest="path",
                      help="Path to the input folder (This parameter is mandatory)",
                      metavar="PATH")

    (options, args) = parser.parse_args()

    # make sure all necessary input parameters are provided
    if not options.path:
        print('Mandatory parameters missing')
        print('')
        parser.print_help()
        sys.exit(1)


    findFailedFiles(options.path)


if __name__ == '__main__':
    main()
