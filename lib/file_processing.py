import errno
import os
import os.path
import pipes
import shutil
import subprocess

HOME_NAME = "Slip"

def all_files_of_type(folder, file_extension):
  """
  Returns a list of all filenames ending with file_extension in folder
  The list is sorted by the number contained in the filename
  """
  all_files = os.listdir(folder)
  all_files = filter(lambda x: x[0] != '.', all_files) # remove hidden files
  all_files = filter(lambda x: os.path.splitext(x)[1] == file_extension, all_files)
  all_files.sort(key = find_file_number)
  return list(map(lambda x: os.path.join(folder, x), all_files)) # add folder to name

def find_file_number(filename):
  """
  Returns the number contained right before the '.' in a filename
  """
  first, second = filename.split('.')
  s = ''
  for i in reversed(range(len(first))):
    if not first[i].isdigit():
      break
    else:
      s = first[i] + s
  return int(s)

def move_to_home(home_name = HOME_NAME):
  """
  Moves up until reaching the home directory and returns a full path to home
  """
  while os.path.split(os.getcwd())[-1] != home_name:
    os.chdir("..")
  return os.getcwd()

def extract_key_frames(video_location, frame_folder):
  """
  Extracts the key frames from the video at video_location and puts them all into frame_folder
  NOTE: frame_folder should not have any frames in it to start

  Returns: timestamps - A list of the second at which every key frame occurs
  """
  full_video_location = pipes.quote(os.path.join(move_to_home(), video_location)) # absolute path

  if (os.path.exists(frame_folder) == False): # try creating the frame folder
    try:
      os.mkdir(frame_folder)
    except OSError as exc:
      if exc.errno != errno.EEXIST:
        raise exc
      pass
  os.chdir(frame_folder)

  filename = video_location.split('/')[-1]
  output_filename = 'output-{0}.txt'.format(filename)
  with open(output_filename, 'w') as out:
    # now the longass ffmpeg command to split the file
    cmd = "ffmpeg -i {0} -vf select='eq(pict_type\,PICT_TYPE_I)' -vsync " \
    "passthrough -s 320x180 -f image2 %03d.png -loglevel debug 2>&1 | grep " \
    "select:1".format(full_video_location)
    p = subprocess.Popen(cmd, shell = True, stdout = out)
    p.wait()
    out.flush()

  timestamps = []
  out_file = open(output_filename,'r')
  for line in out_file:
    # some processing to get the time out of the line
    try:
      time = line.split(' t:')[1].split(' ')[0]
    except IndexError: # for some reason a frame can be missing a timestamp
      time = timestamps[-1] + 1
    time = float(time)

    # decrease time by 1 second so the video starts just before the correct point
    time = max(0, time - 1) # stay positive :D
    timestamps.append(time)

  return timestamps

def split_slides(slide_location, slide_folder):
  """
  Splits a PDF at slide_location to .jpg images in slide_folder

  NOTE: slide_folder should not contain any slides
  """
  move_to_home()
  try: # try to make slide folder if it needs to be made
    os.mkdir(slide_folder)
  except OSError as exc:
    if exc.errno != errno.EEXIST:
      raise exc
    pass

  shutil.move(slide_location, slide_folder)
  os.chdir(slide_folder)
  p = subprocess.Popen("convert {0} slide.jpg".format(slide_location.split('/')[-1]), shell = True)
  p.wait()

  # move slide back
  move_to_home()
  shutil.move(os.path.join(slide_folder, os.path.split(slide_location)[-1]), slide_location)
