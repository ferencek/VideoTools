# Python video tools

A set of Python scripts for transcoding video files.

## Table of contents

* [Software setup](#software-setup)
* [Transcode video files](#transcode-video-files)
* [Optional file operations](#optional-file-operations)
   * [Swap video files](#swap-video-files)
   * [Rotate video files](#rotate-video-files)

## Software setup

**Prerequisites:** `ffmpeg`, `mediainfo`, `python3-pymediainfo`

To use the video tools, clone the repository

```
git clone --depth 1 https://github.com/ferencek/VideoTools.git

cd VideoTools
```

## Transcode video files

The main script in the repository is `transcodeVideoFiles.py`. For instructions on how to run it and to see available command-line options, run

```
python transcodeVideoFiles.py -h
```

To process all video files in a source directory and copy the output into a destination directory, run the script as follows

```
python transcodeVideoFiles.py -s /path/to/source/directory/ -d /path/to/destination/directory/
```

This might take some time depending on the number of video files contained in the source directory. The source and destination directory
paths can be defined as either relative or absolute paths. The above command will first look for all video files in the source directory
and based on their video and audio bitrates, it will select those that need to be transcoded. This step will produce in the current directory
the following output files containing info about all, selected, and skipped video files

```
video_files_all.pkl
video_files_all.txt
video_files_selected.pkl
video_files_selected.txt
video_files_skipped.txt
```

Next, the transcoding step can be initiated by running the same command as before but adding the `-t` option. The `--size` option is also useful
to add

```
python transcodeVideoFiles.py -s /path/to/source/directory/ -d /path/to/destination/directory/ -t --size
```

The above can also be done all in one go by adding the `-t` option the first time the command is run but doing it in two steps is useful in order to
first collect some info on the number of files to be transcoded, etc. before starting the slow transcoding step.

This step will produce two additional text files in the current directory

```
video_files_failed.txt
video_files_processed.txt
```

whose content should be self-explanatory. 

The transcoding step will reproduce the relative path structure from the source directory in the destination directory. In other words, if there
exists a file inside `a/b/c/` relative to the source directory, its transcoded version will also be placed inside `a/b/c/` in the destination directory.

## Optional file operations

### Swap video files

Once the transcoding is done, one typically wants to replace the original with the smaller transcoded files. Since the number of files could be too large
to mnake manual copying practical, the `swapVideoFiles.py` script is provided in the repository that can perform this operation automatically. The script
is run as follows

```
python swapVideoFiles.py -s /path/to/source/directory/ -d /path/to/destination/directory/ -b /path/to/backup/directory/
```

Note that the script will look for the `video_files_processed.txt` file in the current directory and in case it does not find it, it will crash.


### Rotate video files

The `rotateVideoFiles.py` script provided in the repository can be used to rotate those video files with wrong orientation. This is particularly useful
for `mp4` video files for which the rotation can be achieved without re-encoding the video file. This is acomplished by repacking the file and inserting
an appropriate rotation field in the file metadata. Nevetheless, the script also supports file rotation through re-encoding but this is mostly relevant
for non-`mp4` input files. The script is run as follows

```
python rotateVideoFiles.py -l video_files_rotation.txt"
```

where `video_files_rotation.txt` is a text file containing a list video files to be rotated, rotation angles (in degrees) and conversion modes (`repack` or `transcode`)
in the following format

```
/path/to/file1.mp4 :  90 : repack
/path/to/file2.mp4 : -90 : repack
```

The resulting rotated file will be stored in a newly created subfolder `rotated/` in the same location as the original file.
