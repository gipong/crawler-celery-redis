from flask import Flask, request, redirect, url_for, jsonify
from werkzeug.utils import secure_filename
from worker import celery
import os
import hashlib
from datetime import datetime
import celery.states as states
import psycopg2


app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = '/opts/download-data'
app.config['MAX_CONTENT_LENGTH'] = 1024 * 1024 * 1024


@app.route('/add/<int:param1>/<int:param2>')
def add(param1: int, param2: int) -> str:
    task = celery.send_task('tasks.add', args=[param1, param2], kwargs={})
    response = f"<a href='{url_for('check_task', task_id=task.id, external=True)}'>check status of {task.id} </a>"
    return response


@app.route('/check/<string:task_id>')
def check_task(task_id: str) -> str:
    res = celery.AsyncResult(task_id)
    if res.state == states.PENDING:
        return res.state
    else:
        return str(res.result)


@app.route('/fetch/<string:task_name>', methods=['POST'])
def start_fetch_image(task_name: str) -> str:
    if 'tar' not in request.files:
        res = jsonify({'message': 'No file part in the request'})
        res.status_code = 400
        return res

    file = request.files['tar']
    if file:
        filename = secure_filename(file.filename)

        s = hashlib.sha1()
        s.update(str("{}-{}".format(filename, datetime.now().timestamp())).encode('utf-8'))
        filename_id = "{}.tar".format(s.hexdigest())

        file.save(os.path.join('/opts/download-data', filename_id))

    crawler_task = celery.send_task('tasks.start_to_search_image', args=[filename_id, filename], kwargs={})
    crawler_response = f"<a href='{url_for('check_task', task_id=crawler_task.id, external=True)}'>check crawler status of {crawler_task.id} </a>"
    task = celery.send_task('tasks.fetch_image_folder', args=[task_name, filename], kwargs={})
    response = f"<a href='{url_for('check_task', task_id=task.id, external=True)}'>check status of {task.id} </a><br><a href='{url_for('check_task', task_id=crawler_task.id, external=True)}'>check crawler status of {crawler_task.id} </a>"
    return response
