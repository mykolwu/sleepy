from flask import *
from app import app
from werkzeug.utils import secure_filename
import os, re, mimetypes

app.config['BEFORE_FOLDER'] = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))), 'files/before')
app.config['AFTER_FOLDER'] = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))), 'files/after')

# Helper functions

def allowed_file(filename):
  return '.' in filename and filename.rsplit('.', 1)[1] in set(['pdf', 'mp4'])

def save_file(file_part):
  if file_part not in request.files:
    flash('No file part')
    return redirect(request.url)

  file = request.files[file_part]
  if file.filename == '':
    flash('No selected file')
    return redirect(request.url)

  if file and allowed_file(file.filename):
    filename = secure_filename(file.filename)
    file.save(os.path.join(app.config['BEFORE_FOLDER'] + '/' + file_part, filename))

def send_from_directory_wrapper(directory, filename):
  filename = safe_join(directory, filename)
  if not os.path.isabs(filename):
    filename = os.path.join(current_app.root_path, filename)
  try:
    if not os.path.isfile(filename):
      raise NotFound()
  except (TypeError, ValueError):
    raise BadRequest()
  return send_file_partial(filename)

def send_file_partial(path):
  range_header = request.headers.get('Range', None)
  if not range_header:
    return send_file(path)

  size = os.path.getsize(path)    
  byte1, byte2 = 0, None

  m = re.search('(\d+)-(\d*)', range_header)
  g = m.groups()

  if g[0]: byte1 = int(g[0])
  if g[1]: byte2 = int(g[1])

  length = size - byte1
  if byte2 is not None:
    length = byte2 - byte1

  data = None
  with open(path, 'rb') as f:
    f.seek(byte1)
    data = f.read(length)

  rv = Response(data, 206, mimetype=mimetypes.guess_type(path)[0], direct_passthrough=True)
  rv.headers.add('Content-Range', 'bytes {0}-{1}/{2}'.format(byte1, byte1 + length - 1, size))
  return rv

# Endpoints

@app.after_request
def after_request(response):
  response.headers.add('Accept-Ranges', 'bytes')
  return response

@app.route('/upload', methods=['POST'])
def upload_file():
  save_file('video')
  save_file('slides')    
  return render_template('player.html')

@app.route('/slide', methods=['GET'])
def get_slide():
  return send_from_directory(app.config['AFTER_FOLDER'] + '/slides', 'slide-' +
      request.args.get('slidenumber') + '.jpg')

@app.route('/video', methods=['GET'])
def get_video():
  return send_from_directory_wrapper(app.config['BEFORE_FOLDER'] + '/video', 'video.mp4')

@app.route('/timestamps', methods=['GET'])
def get_timestamps():
  return send_from_directory(app.config['AFTER_FOLDER'], 'data.json')

# Templates

@app.route('/player', methods=['GET'])
def player():
  return render_template('player.html')

@app.route('/', methods=['GET'])
def index():
  return render_template('index.html')
