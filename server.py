from flask import Response, Flask, render_template, request, redirect, url_for, jsonify, make_response
from flaskext.mysql import MySQL
import face_recognition
import cv2
import numpy as np
import os
import base64
from flask import session
import json
import pymysql
from flask_cors import CORS
import random
import string

pymysql.install_as_MySQLdb()

app = Flask(__name__)
cors = CORS(app)
app.config['UPLOAD_FOLDER'] = 'static/uploads'


# This is a demo of running face recognition on live video from your webcam. It's a little more complicated than the
# other example, but it includes some basic performance tweaks to make things run a lot faster:
#   1. Process each video frame at 1/4 resolution (though still display it at full resolution)
#   2. Only detect faces in every other frame of video.

# Get a reference to webcam #0 (the default one)
# video_capture = cv2.VideoCapture(0)

global known_face_encodings 
global known_face_names 
known_face_encodings = []
known_face_names = []
load_frame = True

def get_random_string(length):
    # choose from all lowercase letter
    letters = string.ascii_lowercase
    result_str = ''.join(random.choice(letters) for i in range(length))
    return result_str

def load_faces():
    # Set the folder path
    folder_path = app.config['UPLOAD_FOLDER'] + "/imgs"
    info_path = app.config['UPLOAD_FOLDER'] + "/info"

    # Get a list of all the files in the folder
    file_list = os.listdir(folder_path)

    # Filter the list to include only image files
    image_list = [f for f in file_list if f.endswith('.jpg') or f.endswith('.jpeg') or f.endswith('.png')]

    if(len(image_list) == 0):
        return

    # Iterate through the image files
    for name in image_list:
        # Do something with each image file, such as read it into memory or process it
     
        image = face_recognition.load_image_file(folder_path + "/" + name)
        face_encoding = face_recognition.face_encodings(image)[0]
        info_path_file = info_path + "/" + name.split('.')[0] + '.txt'
        with open(info_path_file, 'r', encoding="utf-8") as f:
            file_contents = f.read()

        # Create arrays of known face encodings and their names
        known_face_encodings.append(face_encoding)
        known_face_names.append(file_contents)
    print('------------------')
    print(known_face_names)


# Initialize some variables
face_locations = []
face_encodings = []
face_names = []
process_this_frame = True
global frame1
frame1 = None
global left, right, top, bottom
left = right = top = bottom =None 

def predict(frame):
    if len(known_face_encodings) == 0:
        return "Unknown"
    # Resize frame of video to 1/4 size for faster face recognition processing
    if frame is None:
        return 'Unknown'
    small_frame = cv2.resize(frame, (0, 0), fx=0.2, fy=0.2)
    # small_frame = cv2.resize(frame, (0, 0), dsize=(224,224))

    # Convert the image from BGR color (which OpenCV uses) to RGB color (which face_recognition uses)
    rgb_small_frame = small_frame[:, :, ::-1]
    
    # Find all the faces and face encodings in the current frame of video
    face_locations = face_recognition.face_locations(rgb_small_frame)
    face_encodings = face_recognition.face_encodings(rgb_small_frame, face_locations)

    face_names = []
    for face_encoding in face_encodings:
        # See if the face is a match for the known face(s)
        matches = face_recognition.compare_faces(known_face_encodings, face_encoding)
        name = "Unknown"

        # If a match was found in known_face_encodings, just use the first one.
        if True in matches:
            first_match_index = matches.index(True)
            name = known_face_names[first_match_index]

        # Or instead, use the known face with the smallest distance to the new face
        face_distances = face_recognition.face_distance(known_face_encodings, face_encoding)
        best_match_index = np.argmin(face_distances)
        print(best_match_index)
        if matches[best_match_index]:
            name = known_face_names[best_match_index]

        face_names.append(name)
    # global process_this_frame
    # process_this_frame = not process_this_frame


    # Display the results
    name_res = 'Unknown'
    for (top, right, bottom, left), name in zip(face_locations, face_names):
        # Scale back up face locations since the frame we detected in was scaled to 1/4 size
        top *= 5
        right *= 5
        bottom *= 5
        left *= 5

        # Draw a label with a name below the face
        # cv2.rectangle(frame, (left, bottom - 35), (right, bottom), (0, 0, 255), cv2.FILLED)

        # Set the font and font scale
        font = cv2.FONT_HERSHEY_SIMPLEX
        name_res = name
        cv2.putText(frame, name, (left + 6, bottom - 6), font, 1.0, (255, 255, 255), thickness=2)

    return name_res
    # return frame

# Define the video stream generator function
def gen_frames():
    global load_frame
    video_capture = cv2.VideoCapture(0)
    while load_frame:
        # Read the video stream from the webcam
        success, frame = video_capture.read()
        # frame = predict(frame)
        if not success:
            break
        else:
        
            ret, buffer = cv2.imencode('.jpg', frame)
            frame = buffer.tobytes()
            # Draw a box around the face
            global left, right, top, bottom
            # cv2.rectangle(frame, (left, top), (right, bottom), (0, 0, 255), 2)

            # Yield the frame to the web page
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

@app.route('/predict')
def predict_page():
    load_faces()
    return render_template('predict.html')


@app.route('/capture', methods=['POST'])
def capture():
    # Get user input from form
    name = request.form['name']

    # Capture image from webcam
    random_name = get_random_string(15)
    img_data = request.values['imageBase64']
    filename = app.config['UPLOAD_FOLDER']+"/imgs/"+random_name+".jpg"
    textfilename = os.path.join(app.config['UPLOAD_FOLDER'], f"info/{random_name}.txt")
    with open(filename, "wb") as fh:
        fh.write(base64.b64decode(img_data.split(',')[1]))

    # Save user input to a text file
    with open(textfilename, 'a', encoding="utf-8") as file:
        file.write(f"{name},{filename}\n")

    return 'Image and data saved successfully'

# Define the video stream route
@app.route('/add_face')
def add_face():
    return render_template('add_face.html')
@app.route('/video_feed')
def video_feed():
    return Response(gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

def pred(frame):
    data = predict(frame)
    print('data ------: ',data)
    yield "data: {}\n\n".format(data) 

video_capture1 = cv2.VideoCapture(0)
@app.route("/face_detection")
def face_regco():

    while load_frame:
        success, frame = video_capture1.read()
        try:
            return Response(pred(frame), mimetype="text/event-stream")
        except TypeError:
            return Response("Cannot find faces", mimetype="text/event-stream")

if __name__ == '__main__':
    app.secret_key = 'mysecretkey'
    load_faces()
    app.run(debug=True)
