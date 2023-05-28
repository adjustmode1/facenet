from flask import Response, Flask, render_template, request, redirect, url_for, jsonify, make_response
from flaskext.mysql import MySQL
import face_recognition
import cv2
import numpy as np
import os
import base64
import uuid
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

# app.config["SQLALCHEMY_DATABASE_URI"] = "mysql://root:@localhost/school"

app.config['MYSQL_DATABASE_USER'] = 'root'
app.config['MYSQL_DATABASE_PASSWORD'] = ''
app.config['MYSQL_DATABASE_DB'] = 'school'
app.config['MYSQL_DATABASE_HOST'] = 'localhost'

db = MySQL()
db.init_app(app)

# cursor = mysql.connection.cursor()

# This is a demo of running face recognition on live video from your webcam. It's a little more complicated than the
# other example, but it includes some basic performance tweaks to make things run a lot faster:
#   1. Process each video frame at 1/4 resolution (though still display it at full resolution)
#   2. Only detect faces in every other frame of video.

# Get a reference to webcam #0 (the default one)
video_capture = cv2.VideoCapture(0)

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
        info_path_file = info_path + "/" + name.replace('.jpg', '.txt')
        with open(info_path_file, 'r', encoding="utf-8") as f:
            file_contents = f.read()

        # Create arrays of known face encodings and their names
        known_face_encodings.append(face_encoding)
        known_face_names.append(file_contents)


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
    if frame is None:
        return "Unknown"
    # Resize frame of video to 1/4 size for faster face recognition processing
    try:
        small_frame = cv2.resize(frame, (0, 0), fx=0.2, fy=0.2)

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
    except:
        return 'Unkown'

# Define the video stream generator function
def gen_frames():
    global load_frame
    # video_capture = cv2.VideoCapture(0)
    while True:
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
@app.route('/stop_cam')
def stopcam():
    global load_frame
    load_frame = False

# Define the route for the index page
@app.route('/')
def index():
    conn = db.connect()
    cursor = conn.cursor()
    query = "select * from lophoc;"
    cursor.execute(query)
    cl = cursor.fetchall()
    print(cl)
    return render_template('introdution.html',classes=cl)
# Define the route for the index page

@app.route('/predict')
def predict_page():
    load_faces()
    return render_template('predict.html')

@app.route('/add')
def add_face():
    return render_template('add_face.html')

@app.route('/admin',methods=['GET'])
def admin():
    if 'user' not in session:
        return redirect(url_for('login'))
    conn = db.connect()
    cursor = conn.cursor()
    query = "select * from giaovien;"
    cursor.execute(query)
    gv = cursor.fetchall()
    return render_template('views/admin/giaovien.html',giaoviens=gv,role=session['role'])

@app.route('/cam',methods=['GET'])
def cam():
    load_faces()
    return render_template('predict.html')

@app.route('/admin/classes',methods=['GET'])
def lophoc():
    if 'user' not in session:
        return redirect(url_for('login'))
    conn = db.connect()
    cursor = conn.cursor()
    query = "select * from lophoc;"
    cursor.execute(query)
    classes = cursor.fetchall()
    return render_template('views/admin/classes.html',classes=classes,role=session['role'])

@app.route('/admin/add_class',methods=['POST'])
def add_lophoc():
    if 'user' not in session:
        return redirect(url_for('login'))
    classname = request.form['name']
    try:
        conn = db.connect()
        cursor = conn.cursor()
        query = "insert into lophoc values(\'"+classname.upper()+"\');"
        cursor.execute(query)
        conn.commit()
    except:
        return redirect('/admin/classes')
    return redirect('/admin/classes')

@app.route('/admin/del_class',methods=['POST'])
def del_lophoc():
    if 'user' not in session:
        return redirect(url_for('login'))
    classname = request.form['name']
    try:
        conn = db.connect()
        cursor = conn.cursor()
        query = "delete from lophoc where id=\'"+classname+"\';"
        print(query)
        cursor.execute(query)
        conn.commit()
    except:
        return redirect('/admin/classes')
    return redirect('/admin/classes')

@app.route('/admin/phuhuynh',methods=['GET'])
def phuhuynh():
    if 'user' not in session:
        return redirect(url_for('login'))
    conn = db.connect()
    cursor = conn.cursor()
    query = "select * from phuhuynh;"
    cursor.execute(query)
    ph = cursor.fetchall()
    return render_template('views/admin/phuhuynh.html',phuhuynhs=ph,role=session['role'])

@app.route('/admin/quanly_class',methods=['GET'])
def quanly_class():
    if 'user' not in session:
        return redirect(url_for('login'))
    conn = db.connect()
    cursor = conn.cursor()
    query = "select * from lophoc_hocsinh where id_giaovien=\'"+session['user']+"\'"
    cursor.execute(query)
    lophoc_hocsinh = cursor.fetchall()
    print(lophoc_hocsinh)
    query = "select * from hocsinh;"
    cursor.execute(query)
    hocsinh = cursor.fetchall()
    query = "select * from giaovien"
    cursor.execute(query)
    giaovien = cursor.fetchall()
    return render_template('views/admin/student_class.html',classes=lophoc_hocsinh,role=session['role'])

@app.route('/classes',methods=['GET'])
def classes():
    query = request.args.get('class')
    conn = db.connect()
    cursor = conn.cursor()
    query = "select * from lophoc where id=\'"+query+"\';"
    cursor.execute(query)
    ph = cursor.fetchall()
    return render_template('views/classes.html',phuhuynhs=ph)

@app.route('/classes/<id>',methods=['GET'])
def view_lophoc(id):
    conn = db.connect()
    cursor = conn.cursor()
    query = "select * from lophoc_hocsinh where id_lophoc=\'"+id+"\';"
    cursor.execute(query)
    lh = cursor.fetchall()
    query = "select * from giaovien"
    cursor.execute(query)
    gv = cursor.fetchall()    
    query = "select * from hocsinh"
    cursor.execute(query)
    hocsinh = cursor.fetchall() 
    gvcn = ''
    for x in gv:
        print('x: ',x[1])
        print('x: ',lh[1])
        if x[0] == lh[0]:
            gvcn = gv[1]

    return render_template('views/classes.html',classes=lh,gv=gv,hs=hocsinh,siso=len(lh),giaovienchunhhiem=gvcn)
    
@app.route('/test')
def test():
    return render_template('add_test.html')

@app.route('/admin/login',methods=['GET'])
def login():
    return render_template('views/admin/login.html')

@app.route('/admin/login',methods=['POST'])
def checklogin():
    conn = db.connect()
    cursor = conn.cursor()
    query = "select * from giaovien WHERE id=\'"+request.form['username']+"\' and matkhau = \'"+request.form['password']+"\';"
    cursor.execute(query)
    account = cursor.fetchone()
    print(account)
    if (account is None):
        return redirect(url_for('login'))
    else:
        session['user'] = account[0]
        session['role'] = account[6]
        print(account[6])
        if account[6] == 0:
            return redirect(url_for('admin'))
        else:
            return redirect(url_for('phuhuynh'))
    
@app.route('/admin/logout',methods=['POST'])
def logout():
    if 'user' in session:
        del session['user']
    if 'role' in session:
        del session['role']
    return redirect(url_for('login'))

@app.route('/admin/add_giaovien',methods=['POST'])
def add_giaovien():
    if 'user' not in session:
        return redirect(url_for('login'))
    if 'role' not in session:
        return redirect(url_for('login'))
    if session['role'] != 0:
        return redirect(url_for('login'))
    name = request.form['name']
    code = request.form['code']
    gender = 1
    if request.form['gender'] == 'female':
        gender = 0
    birthday = request.form['birthday']
    password = request.form['password']
    image = request.files['file']
    try:
        conn = db.connect()
        cursor = conn.cursor()
        newimage = get_random_string(15)
        newimage = '/static/uploads/teachers/'+newimage+'.'+image.filename.split('.')[1]
        query = 'insert into giaovien values(\"'+code+'\",\"'+name+'\",\"'+newimage+'\",'+str(gender)+',\"'+birthday+'\",'+'\"'+password+'\"'+',1)'
        print(query)   
        cursor.execute(query)
        conn.commit()
        image.save('/static/uploads/teachers/'+newimage+'.'+image.filename.split('.')[1])
    except:
        return redirect(url_for('admin'))
    return redirect(url_for('admin'))

@app.route('/admin/del_giaovien',methods=['POST'])
def del_giaovien():
    if 'user' not in session:
        return redirect(url_for('login'))
    id = request.form['id']
    conn = db.connect()
    cursor = conn.cursor()
    query = 'delete from giaovien where id=\"'+id+"\";" 
    print(query)
    cursor.execute(query)
    conn.commit()
    return redirect(url_for('admin'))

@app.route('/admin/teacher_class',methods=['GET'])
def teacher_class():
    if 'user' not in session:
        return redirect(url_for('login'))
    conn = db.connect()
    cursor = conn.cursor()
    query = 'select * from lophoc_giaovien' 
    cursor.execute(query)
    lophoc_giaovien = cursor.fetchall()
    query = 'SELECT * FROM lophoc'
    cursor.execute(query)
    lophoc = cursor.fetchall()
    query = 'SELECT * FROM giaovien'
    cursor.execute(query)
    giaovien = cursor.fetchall()
    return render_template('views/admin/teacher_class.html',classes=lophoc_giaovien,lophoc_giaovien=lophoc,giaovien=giaovien,role=session['role'])

@app.route('/admin/add_teacher_class',methods=['POST'])
def add_teacher_class():
    if 'user' not in session:
        return redirect(url_for('login'))
    lophoc = request.form['class']
    giaovien = request.form['teacher']
    conn = db.connect()
    cursor = conn.cursor()
    query = 'insert into lophoc_giaovien values(\"'+lophoc+'\",\"'+giaovien+'\")' 
    cursor.execute(query)
    conn.commit()
    return redirect(url_for('teacher_class'))

@app.route('/admin/del_teacher_class',methods=['POST'])
def del_teacher_class():
    if 'user' not in session:
        return redirect(url_for('login'))
    try:
        lophoc = request.form['class']
        giaovien = request.form['teacher']
        conn = db.connect()
        cursor = conn.cursor()
        query = 'delete from lophoc_giaovien where id_lophoc=\"'+lophoc+'\" and id_giaovien=\"'+giaovien+'\"' 
        cursor.execute(query)
        conn.commit()
    except:
        return redirect(url_for('teacher_class'))
    return redirect(url_for('teacher_class'))

@app.route('/admin/add_phuhuyn',methods=['GET'])
def add_phuhuynh():
    if 'user' not in session:
        return redirect(url_for('login'))
    return render_template('views/admin/addphuhuynh.html',student=-1,role=session['role'])

@app.route('/admin/add_phuhuyn/<id>',methods=['GET'])
def add_phuhuynh_and_student(id):
    if 'user' not in session:
        return redirect(url_for('login'))
    return render_template('views/admin/addphuhuynh.html',classes='',student=id,role=session['role'])

@app.route('/admin/student',methods=['GET'])
def student():
    if 'user' not in session:
        return redirect(url_for('login'))
    conn = db.connect()
    cursor = conn.cursor()
    query = 'select * from hocsinh' 
    cursor.execute(query)
    hocsinh = cursor.fetchall()
    print(hocsinh)
    return render_template('views/admin/student.html',hocsinh=hocsinh,role=session['role'])

@app.route('/admin/add_student',methods=['POST'])
def add_student():
    if 'user' not in session:
        return redirect(url_for('login'))
    if 'role' not in session:
        return redirect(url_for('login'))
    if session['role'] != 1:
        return redirect(url_for('login'))
    name = request.form['name']
    gender = 1
    if request.form['gender'] == 'female':
        gender = 0
    birthday = request.form['birthday']
    image = request.files['file']
    print(image)
    # try:
    conn = db.connect()
    cursor = conn.cursor()
    newimage = get_random_string(15)
    newimage = newimage+'.'+image.filename.split('.')[1]
    query = 'insert into hocsinh(ten,hinhanh,gioitinh,ngaysinh) values(\"'+name+'\",\"'+newimage+'\",'+str(gender)+',\"'+birthday+'\")'
    print(query)   
    cursor.execute(query)
    conn.commit()
    image.save(os.path.join(app.config['UPLOAD_FOLDER'],newimage))
    # except:
        # return redirect(url_for('student'))
    return redirect(url_for('student'))

@app.route('/admin/del_student',methods=['POST'])
def del_student():
    if 'user' not in session:
        return redirect(url_for('login'))
    if 'role' not in session:
        return redirect(url_for('login'))
    if session['role'] != 1:
        return redirect(url_for('login'))
    name = request.form['id']
    try:
        conn = db.connect()
        cursor = conn.cursor()
        query = 'delete from hocsinh where id=\"'+name+'\"'
        print(query)   
        cursor.execute(query)
        conn.commit()
    except:
        return redirect(url_for('student'))
    return redirect(url_for('student'))

@app.route('/admin/del_phuhuynh',methods=['POST'])
def del_phuhuynh():
    id = request.form['id']
    conn = db.connect()
    cursor = conn.cursor()
    query = 'delete from phuhuynh where id=\"'+id+"\""
    cursor.execute(query)
    conn.commit()
    os.remove('static/uploads/imgs/'+id+'.jpg')
    os.remove('static/uploads/info/'+id+'.txt')
    load_faces()
    return redirect(url_for('phuhuynh'))

@app.route('/capture', methods=['POST'])
def capture():
    # Get user input from form
    name = request.form['name']
    birthday = request.form['birthday']
    phone = request.form['phone']
    address = request.form['address']
    gender = 1
    if request.form['gender'] == 'female':
        gender = 0

    # Capture image from webcam
    random_name = get_random_string(15)
    img_data = request.values['imageBase64']
    filename = app.config['UPLOAD_FOLDER']+"/imgs/"+random_name+".jpg"
    textfilename = os.path.join(app.config['UPLOAD_FOLDER'], f"info/{random_name}.txt")
    with open(filename, "wb") as fh:
        fh.write(base64.b64decode(img_data.split(',')[1]))

    # Save user input to a text file
    with open(textfilename, 'a', encoding="utf-8") as file:
        file.write(f"{name},{birthday},{phone},{gender},{address},{filename}\n")

    conn = db.connect()
    cursor = conn.cursor()
    query = 'insert into phuhuynh values(\"'+random_name+'\",\"'+name+'\",\"'+filename+'\",'+str(gender)+',\"'+phone+'\",\"'+birthday+'\",\"'+address+'\")'    
    print(query)
    cursor.execute(query)
    conn.commit()
    if request.form['student']:
        query = 'insert into phuhuynh_hocsinh values(\"'+random_name+'\",\"'+request.form['student']+'\")'
        cursor.execute(query)
        conn.commit()
    return 'Image and data saved successfully'


# Define the video stream route
@app.route('/video_feed')
def video_feed():
    return Response(gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

def pred(frame):
    data = predict(frame)
    print('data; ',data)
    if data == 'Unknown':
        yield "data: {}\n\n".format('Unknown')
    else:
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
