import json
import time
from anyio import sleep
from controller.controller import Controller
from model.OpenAiModel.count_tokens import num_tokens_from_messages
from web_api.dialogue_api import dialogue_api_handler
from flask import Flask, Response, render_template
from flask_restful import Api, reqparse
from flask_cors import CORS
from model.OpenAiModel.envVar import *
from model.OpenAiModel.chat_completion import ChatCompletion
import threading
import requests
from PIL import Image
from io import BytesIO

client = CLIENT


app = Flask(__name__)
api = Api(app)
CORS(app)

MainController = Controller()
dialogue_api_hl = dialogue_api_handler()
global thread1
global thread2
global thread3



_test_thread = client.beta.threads.create()
thread1 = client.beta.threads.create()
thread2 = client.beta.threads.create()
thread3 = client.beta.threads.create()
## create several assistants for different purposes 


parser = reqparse.RequestParser()
parser.add_argument('user_input',type=str,location='json')

def respond(res):
    return {'code':0,'message':'success','res':res}

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/ping")
def ping():
    return "Pong"

@app.route("/echo")
def echo():
    args = parser.parse_args()
    user_request_input = args['user_input']
    return respond(user_request_input)

@app.route("/chat", methods=['POST'])
def chat():
    userInput = parser.parse_args()['user_input']
    if userInput:
        MainController.get_ai_res(userInput)
        print(MainController.output)
        return respond(MainController.output)
    return respond("No input"), 400

user_input = "hi"
global queue

@app.route("/post_accident", methods=['POST'])
def post_accident():
    global queue
    user_input = parser.parse_args()['user_input']
    if user_input and token_check(user_input):
        queue = MainController.post_accident_bot_res(user_input, thread1)
        return respond(user_input)

    return respond("No input"), 400

@app.route("/route_planner", methods=['POST'])
def route_planner():
    global queue
    user_input = parser.parse_args()['user_input']

    if user_input and token_check(user_input):
        queue = MainController.route_planner_res(user_input, thread2)
        return respond(user_input)

    return respond("No input"), 400

@app.route("/route_info", methods=['POST'])
def route_info():
    global queue
    user_input = parser.parse_args()['user_input']
    if user_input and token_check(user_input):
        queue = MainController.route_info_res(user_input, thread3)
        return respond(user_input)

    return respond("No input"), 400

@app.route("/poc", methods=['GET'])
def poc():
    global queue
    def consumer():
        while True:
            try:
                message = queue.get()
                json_object = {"message": message, "isParagraphEnd": False}
                if message.endswith("\n\n"):
                    json_object["isParagraphEnd"] = True 
                yield f"data: {json.dumps(json_object)}\n\n"
            except:
                break

    return Response(consumer(), mimetype='text/event-stream')

@app.route("/stream", methods=['GET'])
def stream():
    def event_stream():
        for i in range(10):
            message = f"data: {time.time()}\n\n"
            print(f" the type of message is {type(message)}")
            yield message  # Send data to frontend
            time.sleep(1)
    return Response(event_stream(), mimetype='text/event-stream')

@app.route("/greeting", methods=['GET'])
def greeting():
    return Response(MainController.greetings())

def token_check(message):
    return len(message) < 4096


prompt_history = ""

app.route("/image", methods = ['GET'])
def image():
    image_url = MainController.get_ai_image_url(prompt_history)  # Replace with your image URL
    response = requests.get(image_url)
    if response.status_code == 200:
        image_data = response.content
        image = Image.open(BytesIO(image_data))
        image.show()  # Display the image
        return "Image displayed successfully"
    else:
        return "Failed to retrieve image"



def modify_thread_msg(modify_thread, message_id, new_content):
    global _test_thread
    global thread1
    global thread2
    global thread3
    
    pre = f"the user modify a message. here is the new message in triple quote delimeter: '''{new_content}"
    pre += "''' please base your reply on the thread messages newly created which are history messages and provide modified answer."
    
    if modify_thread == 1:
        curr_thread_id = thread1.id
        # modify thread 1 (create new thread for each modification)
        thread_messages = client.beta.threads.messages.list(curr_thread_id)
        create_new_thread_messages(modify_thread, message_id, pre + new_content, thread_messages)


    elif modify_thread == 2:
        curr_thread_id = thread2.id
        # modify thread 2
        thread_messages = client.beta.threads.messages.list(curr_thread_id)
        create_new_thread_messages(modify_thread, message_id, pre + new_content, thread_messages)

    elif modify_thread == 3:
        curr_thread_id = thread3.id
        # modify thread 3
        thread_messages = client.beta.threads.messages.list(curr_thread_id)
        create_new_thread_messages(modify_thread, message_id, pre + new_content, thread_messages)
    
    else:
        curr_thread_id = _test_thread.id
        thread_messages = client.beta.threads.messages.list(curr_thread_id)
        create_new_thread_messages(modify_thread, message_id, pre + new_content, thread_messages)


    # retrieve previous msg history
    client.beta.threads.delete(curr_thread_id)

    pass




def create_new_thread_messages(modify_thread, message_id, new_content, thread_messages):
    global _test_thread
    global thread1
    global thread2
    global thread3
    
    new_thread_messages = []
    for i in range(len(thread_messages.data)):
        message = thread_messages.data[len(thread_messages.data) - i - 1]
        if message.id != message_id:
            try:
                new_thread_messages.append({
                    "role": "user",
                    "content": message.content.text.value,
                    })
            except Exception:
                print(f"error in message: {message}")
        else:
            break

    if modify_thread == 1:
        thread1 = client.beta.threads.create(messages = new_thread_messages)
        client.beta.threads.messages.create(thread1.id, role="user", content = new_content)
    elif modify_thread == 2:
        thread2 = client.beta.threads.create(messages = new_thread_messages)
        client.beta.threads.messages.create(thread2.id, role="user", content = new_content)
    elif modify_thread == 3:
        thread3 = client.beta.threads.create(messages = new_thread_messages)
        client.beta.threads.messages.create(thread3.id, role="user", content = new_content)
    else:
        _test_thread = client.beta.threads.create(messages = new_thread_messages)
        client.beta.threads.messages.create(_test_thread.id, role="user", content = new_content)
        print(_test_thread)
'''
print(MainController.route_info_res("hi", thread3))
print(MainController.route_planner_res("hi", thread2))
print(MainController.post_accident_bot_res("hi", thread1))
'''
# print("\n\n\nnow try run route_info_res\n\n\n")


##########################
# Test the event handler #
# ##########################


# def process_stream():
#     MainController.route_info_res("hi, please provide specific road info on a rainy day in singapore, better include pricing models", thread3)

# def monitor_output():
#     output = ""
#     while MainController.isProcessing :
#         if MainController.output and MainController.output != output:
#             print(MainController.output, end = "")
#             output = MainController.output

# # Create threads
# t1 = threading.Thread(target = process_stream)
# t2 = threading.Thread(target = monitor_output)

# Start threads
#t1.start()
#t2.start()

# test image generation
def test_image_generation(prompt_history):
    image_url = MainController.get_ai_image_url(prompt_history)  # Replace with your image URL
    response = requests.get(image_url)
    if response.status_code == 200:
        image_data = response.content
        image = Image.open(BytesIO(image_data))
        image.show()  # Display the image
        return "Image displayed successfully"
    else:
        return "Failed to retrieve image"

######################################
# test image generation delete later #
######################################
# user_msg = input("user input:")
# print("Preparing response...")
# print(ChatCompletion().get_chat_response(user_msg))
# print("Preparing image...")
# print(test_image_generation(ChatCompletion().get_chat_response(user_msg)))


if __name__ == '__main__':
    print("Starting server on port :80")
    app.run(host='0.0.0.0', port=80, debug=True)


