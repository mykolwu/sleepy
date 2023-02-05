from celery import Celery
import cv2
import json
import math
import pytesseract
try:
  import Image
except ImportError:
  from PIL import Image

OCR_IMAGE_SIZE = 512
FRAME_IMAGE_SIZE = 200
SLIDE_IMAGE_SIZE = 500

MATCH_THRESHOLD = 0.6

app = Celery('tasks', backend='rpc://', broker='pyamqp://')

def match(slide_filenames, frame_filenames):
  """
  Matches up slides and frames 
  
  Args:
    slide_filenames -- Generator containing the filename of slide images
    frame_filenames -- Same as above but for frames

  Returns:
    A list containing the frame index that corresponds to each slide
  """
  print "Preprocessing"
  frame_features, frame_text = open_files(frame_filenames, FRAME_IMAGE_SIZE, "frames")
  slide_features, slide_text = open_files(slide_filenames, SLIDE_IMAGE_SIZE, "slides")
  print "Done preprocessing"

  print "Creating grid"
  grid = feature_grid(frame_features, slide_features)
  print "Done creating grid"

  print "Preliminary matches"
  firstList = determine_best_frames(grid)
  print "Done preliminary matches"

  print "Data processing"
  add_text(grid, firstList, slide_text, frame_text)
  final_list = determine_best_frames(grid)
  slide_borders = match_middle(grid, final_list)
  answer = []
  for border in slide_borders:
    answer.append(border[0])
  print "Done data processing"

  return answer

#-------ALGORITHMS-------------------------------------------------------------

def feature_grid(frame_features, slide_features):
  """
  Creates a grid of the number of SIFT matches of each pair of frame and slide
  """
  grid = []
  count = 0
  for slide in slide_features:
    grid.append([])
    match_quality = []
    for i, frame in enumerate(frame_features):
      bf = cv2.BFMatcher()
      matches = bf.knnMatch(frame, slide, k=2)
      num_matches = 0
      for m,n in matches:
        if m.distance < MATCH_THRESHOLD * n.distance:
          num_matches += 1
      match_quality.append((num_matches,i+1))
      grid[-1].append(num_matches)
    count += 1
    print "{0}/{1} 88".format(count,len(slide_features))
  return grid

def determine_best_frames(grid):
  """
  Matches up all the frames and slides in the most effective way possible
  
  Assumptions:
    Every slide appears only once - yes this is wrong but it works well enough for now
    Every slide appears later in the video then the previous one
  Goal:
    Trace a path from the top of the grid to the bottom. Whenever moving down,
    you must move right some number of steps. Maximize the the sum of this path
  Solution:
    Dynamic Programming - ask Guy if you want help understanding. Hopefully he didn't
              forget how it works
  """
  normalize(grid)
  num_frames = len(grid[0])
  num_slides = len(grid)
  pointers = []
  score = []
  for i in range(len(grid)):
    pointers.append([])
    score.append([0] * len(grid[i]))
    for j in range(len(grid[i])):
      pointers[-1].append(j)

  currentRow = 0
  score[0][0] = grid[0][0]
  for i in range(1, num_frames):
    if score[0][i - 1] >= grid[0][i]:
      score[0][i] = score[0][i - 1]
      pointers[0][i] = pointers[0][i - 1]
    else:
      score[0][i] = grid[0][i]

  for row in range(1, num_slides):
    starting = row
    score[row][starting] = score[row - 1][starting - 1] + grid[row][starting]
    for col in range(row + 1, num_frames):
      newScore = score[row - 1][col - 1] + grid[row][col]
      if score[row][col - 1] >= newScore:
        score[row][col] = score[row][col - 1]
        pointers[row][col] = pointers[row][col - 1]
      else:
        score[row][col] = newScore

  answers = []
  currentFrame = pointers[-1][-1]
  answers.append(currentFrame)
  currentRow = num_slides - 1
  while currentRow != 0:
    currentRow -= 1
    currentFrame = pointers[currentRow][currentFrame - 1]
    answers.append(currentFrame)

  x = list(reversed(answers))
  return x

def match_middle(grid, slide_middles):
  """
  Expands slides to take up a range of values instead of only the middle
  """
  threshold = 0.2
  first_slide_amount = grid[0][slide_middles[0]] * threshold
  start = slide_middles[0]
  while start > 0 and grid[0][start - 1] >= first_slide_amount:
    start -= 1

  end_slide_amount = grid[-1][slide_middles[-1]] * threshold
  end = slide_middles[-1]
  while end < len(grid[0]) - 1 and  grid[-1][end + 1] >= end_slide_amount:
    end += 1

  dividers = []
  for i in range(len(grid) - 1):
    best_divider = None
    best_metric = -1
    for divider_position in range(slide_middles[i], slide_middles[i + 1]):
      metric = 0
      for slide in range(slide_middles[i], divider_position + 1):
        metric += grid[i][slide]
      for slide in range(divider_position + 1, slide_middles[i + 1] + 1):
        metric += grid[i + 1][slide]
      if metric > best_metric:
        best_metric = metric
        best_divider = divider_position
    dividers.append(best_divider)

  borders = []
  borders.append([start, dividers[0]])
  for i in range(len(dividers) - 1):
    borders.append([dividers[i] + 1, dividers[i + 1]])
  borders.append([dividers[-1] + 1, end])
  return borders

def add_text(grid, slide_middles, slide_text, frame_text):
  """
  Adds text matching to the grid
  """
  for i, line in enumerate(grid):
    if i < 2:
      lower = 0
    else:
      lower = slide_middles[i - 2]
    if i >= len(slide_middles) - 2:
      higher = len(grid[0]) - 1
    else:
      higher = slide_middles[i + 2]
    text_matches = []
    for frame in range(lower, higher + 1):
      text_matches.append(text_compare(slide_text[i], frame_text[frame]))
    normalize_row(text_matches)
    for frame in range(lower, higher + 1):
      grid[i][frame] += text_matches[frame - lower]
      grid[i][frame] /= 2

def normalize(grid):
  """
  Normalizes every row in a grid so the maximum is 1
  MODIFIES IN PLACE
  """
  for row in range(len(grid)):
    max_value = max(grid[row])
    if max_value != 0:
      for col in range(len(grid[row])):
        grid[row][col] /= float(max_value) # prevent issues with integer round down

def normalize_row(row):
  """
  Same as above but for one run
  """
  max_value = max(row)
  if max_value != 0:
    for col in range(len(row)):
      row[col] /= float(max_value)

#-------FILE UTILITIES---------------------------------------------------------

@app.task
def run(name, target_size):
  image = cv2.imread(name)
  image = resize(image, target_size)
  sift = cv2.xfeatures2d.SIFT_create()
  return (str(sift.detectAndCompute(image, None)[1]), filename_to_str(name))
  # features[count] = sift.detectAndCompute(image, None)[1]
  # text[count] = filename_to_str(name)

def open_files(filenames, target_size, debug = None):
  """
  Opens a list of files and returns SIFT features as well as slide text
  
  Args:
    filenames: List of the filenames of images
    target_size: A scale of how big the image should be after opening
  
  Returns:
    (features, text)
    features -> list of SIFT features of each image
    text -> OCR text extracted from each image
  """
  print "\tStarting", debug
  from slide_match import run

  result_set = [None] * len(filenames)
  count = 0
  for name in filenames:
    result_set[count] = run.delay(name, target_size)
    count += 1
    print "{0}/{1} 255".format(count,len(filenames))

  finish = False
  while not finish:
    finish = True
    count = 0
    for result in result_set:
      count += 1
      if not result.successful():
        finish = False
        break
    print count

  features = [None] * len(filenames)
  text = [None] * len(filenames)
  for i in range(len(filenames)):
    result = result_set[i].result
    print result
    features[i] = json.loads(result[0])
    text[i] = result[1]

  print features, text
  return (features, text)

def filename_to_str(filename):
  """
  Uses tesseract OCR to open an image at filename and return its text
  """
  try:
    image = Image.open(filename)
    image.thumbnail((OCR_IMAGE_SIZE, OCR_IMAGE_SIZE))

    if len(image.split()) == 4:
      # In case we have 4 channels, lets discard the Alpha.
      # Kind of a hack, should fix in the future some time.
      r, g, b, a = image.split()
      image = Image.merge("RGB", (r, g, b))
  except IOError:
    sys.stderr.write('ERROR: Could not open file "%s"\n' % filename)
    exit(1)
  # try:
  return pytesseract.image_to_string(image).encode('unicode-escape', 'ignore')
  # except UnicodeDecodeError:
  #   print pytesseract.image_to_string(image)
  #   return ''

def find_file_number(filename):
  """
  Gives the number at the end of a file filename

  Example: find_file_number("a022.pdf") -> 22
  """
  first, second = filename.split('.')
  s = ''
  for i in reversed(range(len(first))):
    if not first[i].isdigit():
      break
    else:
      s = first[i] + s
  return int(s)

#-------IMAGE UTILITIES--------------------------------------------------------

def resize(image, target):
  """
  Scales down the an open cv image
  
  Args:
    image -- an opencv image
    target -- An upperbound on the smaller dimension
  
  Returns: A scaled down image where the smaller dimension <= target
  """
  smaller = min(image.shape[:2])
  factor = 1.0
  while smaller > target:
    smaller /= 2
    factor /= 2
  return cv2.resize(image, (0,0), fx = factor, fy = factor)

#-------STRING UTILITIES-------------------------------------------------------

def text_compare(slide_text, frame_text):
  """
  Returns a metric of how similar the text on a slide and frame are
  
  Args:
    slide_text - text on the slide
    frame_text - text on the frame
  
  Returns: Metric based on longest common subsequence
  """
  lcs_length = lcs(slide_text, frame_text)
  if len(frame_text) != 0: 
    # penalize for just having a ton of frame_text
    return lcs_length * math.sqrt((len(slide_text) + 0.0) / len(frame_text))
  else:
    return 0

# Source: http://rosettacode.org/wiki/Longest_common_subsequence#Python
def lcs(a, b):
  """
  Returns the length of the Longest cd common subsequence of a and b
  """
  lengths = [[0 for j in range(len(b) + 1)] for i in range(len(a) + 1)]
  # row 0 and column 0 are initialized to 0 already
  for i, x in enumerate(a):
    for j, y in enumerate(b):
      if x == y:
        lengths[i + 1][j + 1] = lengths[i][j] + 1
      else:
        lengths[i + 1][j + 1] = max(lengths[i + 1][j], lengths[i][j + 1])

  # read the substring out from the matrix
  result = 0
  x, y = len(a), len(b)
  while x != 0 and y != 0:
    if lengths[x][y] == lengths[x - 1][y]:
      x -= 1
    elif lengths[x][y] == lengths[x][y - 1]:
      y -= 1
    else:
      assert a[x - 1] == b[y - 1]
      result = 1 + result
      x -= 1
      y -= 1
  return result
