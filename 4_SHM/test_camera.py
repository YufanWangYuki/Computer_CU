# -*- coding: utf-8 -*-
"""
Created on Wed Feb 26 15:28:47 2020

@author: lenovo
"""
import time
import cv2
import torch 
#import pdb
import argparse
import numpy as np
import os 
from collections import OrderedDict
import torch.nn.functional as F
from multiprocessing import Pool

parser = argparse.ArgumentParser(description='human matting')
parser.add_argument('--model', default='model_obj_2.pth', help='preTrained model')
parser.add_argument('--without_gpu', action='store_true', default=True, help='use cpu')

args = parser.parse_args()

torch.set_grad_enabled(False)
INPUT_SIZE = 256

BACKGROUND_PATH = './columbia.jpg'
#################################
#----------------
if args.without_gpu:
    print("use CPU !")
    device = torch.device('cpu')
else:
    if torch.cuda.is_available():
        n_gpu = torch.cuda.device_count()
        print("----------------------------------------------------------")
        print("|       use GPU !      ||   Available GPU number is {} !  |".format(n_gpu))
        print("----------------------------------------------------------")

        device = torch.device('cuda:0,1')

#################################
#---------------
def load_model(args):
    print('Loading model from {}...'.format(args.model))
    if args.without_gpu:
        myModel = torch.load(args.model, map_location=lambda storage, loc: storage)
    else:
        myModel = torch.load(args.model)
    myModel.eval()
    myModel.to(device)
    
    return myModel

def seg_process(args, image, net, img_back):

    # opencv
    origin_h, origin_w, c = image.shape
    image_resize = cv2.resize(image, (INPUT_SIZE,INPUT_SIZE), interpolation=cv2.INTER_CUBIC)
    image_resize = (image_resize - (104., 112., 121.,)) / 255.0


    tensor_4D = torch.FloatTensor(1, 3, INPUT_SIZE, INPUT_SIZE)
    
    tensor_4D[0,:,:,:] = torch.FloatTensor(image_resize.transpose(2,0,1))
    inputs = tensor_4D.to(device)
    # -----------------------------------------------------------------

    t0 = time.time()

    seg, alpha = net(inputs)
    
    print((time.time() - t0))  

    if args.without_gpu:
        alpha_np = alpha[0,0,:,:].data.numpy()
    else:
        alpha_np = alpha[0,0,:,:].cpu().data.numpy()


    fg_alpha = cv2.resize(alpha_np, (origin_w, origin_h), interpolation=cv2.INTER_CUBIC)


    # -----------------------------------------------------------------
    fg = np.multiply(fg_alpha[..., np.newaxis], image)


    # gray
    bg = image
    bg_alpha = 1 - fg_alpha[..., np.newaxis]
    bg_alpha[bg_alpha<0] = 0

    
    bg_gray = np.multiply(bg_alpha, image)

    bg_gray = cv2.cvtColor(bg_gray, cv2.COLOR_BGR2GRAY)
    
    bg[:,:,0] = 0
    bg[:,:,1] = 0
    bg[:,:,2] = 0
    
    # fg : olor, bg : gray
    out = fg + bg

    out[out<0] = 0
    out[out>255] = 255
    out = out.astype(np.uint8)

    return out

def camera_seg(args, net, img_back):

    videoCapture = cv2.VideoCapture(0)
    
    
    flag = True
    while(1):
        start = time.time()
        # get a frame
        ret, frame = videoCapture.read()
        frame = cv2.flip(frame,1)
        origin_h, origin_w, c = frame.shape
        
        if flag is True:
            img_back = cv2.resize(img_back, dsize = (origin_w, origin_h))
            flag = False
            
        frame_seg = seg_process(args, frame, net, img_back)
        cv2.imshow("capture", frame_seg)
        print("-" * 20 + "Total time is" + "-" * 20)
        print((time.time() - start))  
        
        if cv2.waitKey(1) & 0xFF == ord('q'):
            videoCapture.release()
            cv2.destroyAllWindows()
            break
    videoCapture.release()

def main(args):

    myModel = load_model(args)
    img_back = cv2.imread(BACKGROUND_PATH)
     
    camera_seg(args, myModel, img_back)


if __name__ == "__main__":
    main(args)


