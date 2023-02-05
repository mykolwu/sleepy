import lib.backend as backend

SLIDE_LOCATION = 'files/before/slides/slides.pdf'
VIDEO_LOCATION = 'files/before/video/video.mp4'
SLIDE_FOLDER = 'files/after/slides'
FRAME_FOLDER = 'files/after/frames'

backend.find_frames(SLIDE_LOCATION, VIDEO_LOCATION, SLIDE_FOLDER, FRAME_FOLDER)
