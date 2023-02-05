import file_processing
import json
import slide_match

def find_frames(slide_location, video_location, slide_folder, frame_folder):
  """Processes everything and returns a json

  IMPORTANT: slide_folder and frame_folder should initially be empty

  Args:
    slide_location - location of slides relative to home (pdf)
    video_location - location of the video relative to home (mp4)
    slide_folder - A folder to put the slides in
    frame_folder - A folder to put the frames in

  Returns: 
    JSON array where each element represents one frame containing:
      image -> filename inside frame_folder
      timestampe -> time in the video for that frame
  """
  print 'Splitting video'
  timestamps = file_processing.extract_key_frames(video_location, frame_folder)
  print 'Done splitting video'

  print 'Splitting slides'
  file_processing.split_slides(slide_location, slide_folder)
  print "Done splitting slides"

  frame_names = file_processing.all_files_of_type(frame_folder, '.png')
  slide_names = file_processing.all_files_of_type(slide_folder, '.jpg')
  frame_positions = slide_match.match(slide_names, frame_names)

  times = list(timestamps[i] for i in frame_positions) # now get timestamp for each frame

  frames = [] # making the JSON to return
  for i, filename in enumerate(slide_names):
    frame_object = {}
    frame_object['image'] = filename.split('/')[-1] # filename without path
    frame_object['timestamp'] = times[i]
    frames.append(frame_object)

  return json.dumps(frames)
