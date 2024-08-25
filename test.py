

import os 
import replicate

input = {
    "input_image": "https://edgewize.imgix.net/images/wave/2024-07-27%2015:37:21.875266.png",
    "nms": 0.3,
    "conf": 0.3,
    "tsize": 640,
    "model_name": "yolox-s",
    "return_json": True
}

output = replicate.run(
    "daanelson/yolox:ae0d70cebf6afb2ac4f5e4375eb599c178238b312c8325a9a114827ba869e3e9",
    input=input
)
print(output)